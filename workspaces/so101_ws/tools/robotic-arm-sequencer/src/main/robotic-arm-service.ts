import { SQLiteDatabase } from './database';
import { SerialPortManager } from './serial-port-manager';
import { CommandBuilder } from './command-builder';
import { ProjectCache } from './project-cache';
import {
  ActionProject,
  ActionFrame,
  ExecutionOptions,
  ExecutionProgress,
  ExecutionState,
  Mp3Command,
  SerialError,
  DatabaseError
} from '../shared/types';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';
import { ValidationService } from '../shared/validation';
import { randomUUID } from 'crypto';

/**
 * Operation for undo/redo system
 */
interface Operation {
  type: 'add' | 'insert' | 'update' | 'delete' | 'reorder';
  projectId: string;
  data: any;
  inverse: () => Promise<void>;
}

/**
 * Main backend service integrating database and serial communication
 * Provides high-level operations for project management and sequence execution
 */
export class RoboticArmService {
  private db: SQLiteDatabase;
  private serialPort: SerialPortManager;
  private commandBuilder: CommandBuilder;
  private cache: ProjectCache;
  private executionState: ExecutionState = 'idle';
  private currentExecution: {
    frames: ActionFrame[];
    currentIndex: number;
    options: ExecutionOptions;
    abortController: AbortController;
  } | null = null;
  
  // Undo/Redo system (max 20 operations)
  private undoStack: Operation[] = [];
  private redoStack: Operation[] = [];
  private maxUndoStackSize = 20;

  constructor(db: SQLiteDatabase, serialPort: SerialPortManager, cacheSize: number = 20) {
    this.db = db;
    this.serialPort = serialPort;
    this.commandBuilder = new CommandBuilder();
    this.cache = new ProjectCache(cacheSize);
    
    // Warm up cache with recent projects
    this.warmUpCache();
  }

  /**
   * Warm up cache with recently modified projects
   */
  private warmUpCache(): void {
    try {
      const projects = this.db.loadAllActionProjects();
      this.cache.warmUp(projects);
    } catch (error) {
      console.error('Failed to warm up cache:', error);
    }
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return this.cache.getStats();
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  // ==================== Project CRUD Operations ====================

  /**
   * Create a new project
   */
  async createProject(project: Omit<ActionProject, 'id'>): Promise<string> {
    try {
      const newProject = ActionProjectFactory.create({
        name: project.name,
        frames: project.frames || [],
        remoteSlotId: project.remoteSlotId
      });

      this.db.saveActionProject(newProject);
      return newProject.id;
    } catch (error) {
      throw new DatabaseError(`Failed to create project: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Get a project by ID
   */
  async getProject(id: string): Promise<ActionProject | null> {
    try {
      // Check cache first
      const cached = this.cache.get(id);
      if (cached) {
        return cached;
      }

      // Load from database
      const project = this.db.loadActionProject(id);
      
      // Store in cache
      if (project) {
        this.cache.set(id, project);
      }
      
      return project;
    } catch (error) {
      throw new DatabaseError(`Failed to get project: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Get all projects
   */
  async getAllProjects(): Promise<ActionProject[]> {
    try {
      return this.db.loadAllActionProjects();
    } catch (error) {
      throw new DatabaseError(`Failed to get all projects: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Update a project
   */
  async updateProject(project: ActionProject): Promise<void> {
    try {
      // Validate project
      const validation = ValidationService.validateProject(project);
      if (!validation.isValid) {
        throw new DatabaseError(`Invalid project: ${validation.errors.join(', ')}`);
      }

      // Update modified timestamp
      project.modifiedAt = Date.now();
      
      this.db.saveActionProject(project);
      
      // Update cache
      this.cache.set(project.id, project);
    } catch (error) {
      throw new DatabaseError(`Failed to update project: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Delete a project
   */
  async deleteProject(id: string): Promise<void> {
    try {
      this.db.deleteProject(id);
      
      // Remove from cache
      this.cache.delete(id);
    } catch (error) {
      throw new DatabaseError(`Failed to delete project: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Get all projects metadata (lazy loading - no frame data)
   */
  async getAllProjectsMetadata(): Promise<Array<{
    id: string;
    name: string;
    remoteSlotId?: number;
    createdAt: number;
    modifiedAt: number;
    frameCount: number;
    totalDuration: number;
  }>> {
    try {
      const metadata = this.db.getAllProjectsMetadata();
      return metadata.map(item => ({
        id: item.project.id,
        name: item.project.name,
        remoteSlotId: item.project.remote_slot_id,
        createdAt: item.project.created_at,
        modifiedAt: item.project.modified_at,
        frameCount: item.frameCount,
        totalDuration: item.totalDuration
      }));
    } catch (error) {
      throw new DatabaseError(`Failed to get projects metadata: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  // ==================== Frame Operations ====================

  /**
   * Add a frame to the end of the sequence (private, no undo tracking)
   */
  private async _addFrameNoUndo(projectId: string, frame: ActionFrame): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) {
      throw new DatabaseError(`Project ${projectId} not found`);
    }

    // Validate frame
    const validation = ValidationService.validateFrame(frame);
    if (!validation.isValid) {
      throw new DatabaseError(`Invalid frame: ${validation.errors.join(', ')}`);
    }

    // Set sequence ID to next available
    frame.sequenceId = project.frames.length;
    
    // Add frame to project
    project.frames.push(frame);
    project.modifiedAt = Date.now();
    
    await this.updateProject(project);
  }

  /**
   * Add a frame to the end of the sequence
   */
  async addFrame(projectId: string, frame: ActionFrame): Promise<void> {
    try {
      // Store the index for undo
      const project = await this.getProject(projectId);
      if (!project) {
        throw new DatabaseError(`Project ${projectId} not found`);
      }
      const addedIndex = project.frames.length;
      
      // Perform the add
      await this._addFrameNoUndo(projectId, frame);

      // Add to undo stack
      this.addToUndoStack({
        type: 'add',
        projectId,
        data: { frame, index: addedIndex },
        inverse: async () => {
          await this._deleteFrameNoUndo(projectId, addedIndex);
        }
      });
    } catch (error) {
      throw new DatabaseError(`Failed to add frame: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Insert a frame at a specific position (private, no undo tracking)
   */
  private async _insertFrameNoUndo(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) {
      throw new DatabaseError(`Project ${projectId} not found`);
    }

    if (index < 0 || index > project.frames.length) {
      throw new DatabaseError(`Invalid index: ${index}`);
    }

    // Validate frame
    const validation = ValidationService.validateFrame(frame);
    if (!validation.isValid) {
      throw new DatabaseError(`Invalid frame: ${validation.errors.join(', ')}`);
    }

    // Insert frame at index
    project.frames.splice(index, 0, frame);
    
    // Renumber all frames
    this.renumberFrames(project.frames);
    project.modifiedAt = Date.now();
    
    await this.updateProject(project);
  }

  /**
   * Insert a frame at a specific position
   */
  async insertFrame(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    try {
      // Perform the insert
      await this._insertFrameNoUndo(projectId, index, frame);

      // Add to undo stack
      this.addToUndoStack({
        type: 'insert',
        projectId,
        data: { index, frame },
        inverse: async () => {
          await this._deleteFrameNoUndo(projectId, index);
        }
      });
    } catch (error) {
      throw new DatabaseError(`Failed to insert frame: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Update a frame at a specific index (private, no undo tracking)
   */
  private async _updateFrameNoUndo(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) {
      throw new DatabaseError(`Project ${projectId} not found`);
    }

    if (index < 0 || index >= project.frames.length) {
      throw new DatabaseError(`Invalid index: ${index}`);
    }

    // Validate frame
    const validation = ValidationService.validateFrame(frame);
    if (!validation.isValid) {
      throw new DatabaseError(`Invalid frame: ${validation.errors.join(', ')}`);
    }

    // Update frame (preserve sequenceId)
    frame.sequenceId = project.frames[index].sequenceId;
    project.frames[index] = frame;
    project.modifiedAt = Date.now();
    
    await this.updateProject(project);
  }

  /**
   * Update a frame at a specific index
   */
  async updateFrame(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    try {
      const project = await this.getProject(projectId);
      if (!project) {
        throw new DatabaseError(`Project ${projectId} not found`);
      }

      if (index < 0 || index >= project.frames.length) {
        throw new DatabaseError(`Invalid index: ${index}`);
      }

      // Store old frame for undo
      const oldFrame = { ...project.frames[index] };

      // Perform the update
      await this._updateFrameNoUndo(projectId, index, frame);

      // Add to undo stack
      this.addToUndoStack({
        type: 'update',
        projectId,
        data: { index, oldFrame, newFrame: frame },
        inverse: async () => {
          await this._updateFrameNoUndo(projectId, index, oldFrame);
        }
      });
    } catch (error) {
      throw new DatabaseError(`Failed to update frame: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Delete a frame at a specific index (private, no undo tracking)
   */
  private async _deleteFrameNoUndo(projectId: string, index: number): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) {
      throw new DatabaseError(`Project ${projectId} not found`);
    }

    if (index < 0 || index >= project.frames.length) {
      throw new DatabaseError(`Invalid index: ${index}`);
    }

    // Remove frame
    project.frames.splice(index, 1);
    
    // Renumber remaining frames
    this.renumberFrames(project.frames);
    project.modifiedAt = Date.now();
    
    await this.updateProject(project);
  }

  /**
   * Delete a frame at a specific index
   */
  async deleteFrame(projectId: string, index: number): Promise<void> {
    try {
      const project = await this.getProject(projectId);
      if (!project) {
        throw new DatabaseError(`Project ${projectId} not found`);
      }

      if (index < 0 || index >= project.frames.length) {
        throw new DatabaseError(`Invalid index: ${index}`);
      }

      // Store deleted frame for undo
      const deletedFrame = { ...project.frames[index] };

      // Perform the delete
      await this._deleteFrameNoUndo(projectId, index);

      // Add to undo stack
      this.addToUndoStack({
        type: 'delete',
        projectId,
        data: { index, frame: deletedFrame },
        inverse: async () => {
          await this._insertFrameNoUndo(projectId, index, deletedFrame);
        }
      });
    } catch (error) {
      throw new DatabaseError(`Failed to delete frame: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Reorder frames using new order array (private, no undo tracking)
   */
  private async _reorderFramesNoUndo(projectId: string, newOrder: number[]): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) {
      throw new DatabaseError(`Project ${projectId} not found`);
    }

    if (newOrder.length !== project.frames.length) {
      throw new DatabaseError(`Invalid order array length: ${newOrder.length}, expected ${project.frames.length}`);
    }

    // Validate that newOrder contains all indices exactly once
    const sortedOrder = [...newOrder].sort((a, b) => a - b);
    for (let i = 0; i < sortedOrder.length; i++) {
      if (sortedOrder[i] !== i) {
        throw new DatabaseError(`Invalid order array: missing or duplicate index ${i}`);
      }
    }

    // Reorder frames
    const reorderedFrames = newOrder.map(oldIndex => project.frames[oldIndex]);
    project.frames = reorderedFrames;
    
    // Renumber frames
    this.renumberFrames(project.frames);
    project.modifiedAt = Date.now();
    
    await this.updateProject(project);
  }

  /**
   * Reorder frames using new order array
   */
  async reorderFrames(projectId: string, newOrder: number[]): Promise<void> {
    try {
      const project = await this.getProject(projectId);
      if (!project) {
        throw new DatabaseError(`Project ${projectId} not found`);
      }

      // Store old order for undo
      const oldOrder = project.frames.map((_, i) => i);

      // Perform the reorder
      await this._reorderFramesNoUndo(projectId, newOrder);

      // Add to undo stack
      this.addToUndoStack({
        type: 'reorder',
        projectId,
        data: { oldOrder, newOrder },
        inverse: async () => {
          await this._reorderFramesNoUndo(projectId, oldOrder);
        }
      });
    } catch (error) {
      throw new DatabaseError(`Failed to reorder frames: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Renumber frames to ensure consecutive sequenceIds starting from 0
   */
  private renumberFrames(frames: ActionFrame[]): void {
    frames.forEach((frame, index) => {
      frame.sequenceId = index;
    });
  }

  // ==================== Undo/Redo System ====================

  /**
   * Add operation to undo stack
   */
  private addToUndoStack(operation: Operation): void {
    this.undoStack.push(operation);
    
    // Limit stack size
    if (this.undoStack.length > this.maxUndoStackSize) {
      this.undoStack.shift();
    }
    
    // Clear redo stack when new operation is added
    this.redoStack = [];
  }

  /**
   * Undo last operation
   */
  async undo(): Promise<void> {
    if (this.undoStack.length === 0) {
      throw new Error('Nothing to undo');
    }

    const operation = this.undoStack.pop()!;
    
    // Execute inverse operation
    await operation.inverse();
    
    // Add to redo stack
    this.redoStack.push(operation);
    
    // Limit redo stack size
    if (this.redoStack.length > this.maxUndoStackSize) {
      this.redoStack.shift();
    }
  }

  /**
   * Redo last undone operation
   */
  async redo(): Promise<void> {
    if (this.redoStack.length === 0) {
      throw new Error('Nothing to redo');
    }

    const operation = this.redoStack.pop()!;
    
    // Temporarily disable undo tracking to avoid circular additions
    const originalUndoStack = [...this.undoStack];
    
    // Re-execute the operation based on type
    const project = await this.getProject(operation.projectId);
    if (!project) {
      throw new DatabaseError(`Project ${operation.projectId} not found`);
    }

    try {
      switch (operation.type) {
        case 'add':
          // Manually add without going through addFrame to avoid undo stack
          project.frames.push(operation.data.frame);
          project.frames.forEach((frame, index) => {
            frame.sequenceId = index;
          });
          project.modifiedAt = Date.now();
          await this.updateProject(project);
          break;
          
        case 'insert':
          // Manually insert without going through insertFrame
          project.frames.splice(operation.data.index, 0, operation.data.frame);
          this.renumberFrames(project.frames);
          project.modifiedAt = Date.now();
          await this.updateProject(project);
          break;
          
        case 'update':
          // Manually update without going through updateFrame
          operation.data.newFrame.sequenceId = project.frames[operation.data.index].sequenceId;
          project.frames[operation.data.index] = operation.data.newFrame;
          project.modifiedAt = Date.now();
          await this.updateProject(project);
          break;
          
        case 'delete':
          // Manually delete without going through deleteFrame
          project.frames.splice(operation.data.index, 1);
          this.renumberFrames(project.frames);
          project.modifiedAt = Date.now();
          await this.updateProject(project);
          break;
          
        case 'reorder':
          // Manually reorder without going through reorderFrames
          const reorderedFrames = operation.data.newOrder.map((oldIndex: number) => project.frames[oldIndex]);
          project.frames = reorderedFrames;
          this.renumberFrames(project.frames);
          project.modifiedAt = Date.now();
          await this.updateProject(project);
          break;
      }
      
      // Restore undo stack and add the operation back
      this.undoStack = originalUndoStack;
      this.undoStack.push(operation);
      
      // Limit stack size
      if (this.undoStack.length > this.maxUndoStackSize) {
        this.undoStack.shift();
      }
    } catch (error) {
      // Restore undo stack on error
      this.undoStack = originalUndoStack;
      // Re-add to redo stack on error
      this.redoStack.push(operation);
      throw error;
    }
  }

  /**
   * Check if undo is available
   */
  canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  /**
   * Check if redo is available
   */
  canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  // ==================== Sequence Execution ====================

  /**
   * Execute a single frame
   */
  async executeFrame(frame: ActionFrame): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    try {
      // Send MP3 command if sound is assigned
      if (frame.soundId) {
        const mp3Command: Mp3Command = { type: 'play', trackId: frame.soundId };
        const mp3CommandStr = this.commandBuilder.buildMp3Command(mp3Command);
        await this.serialPort.sendCommand(mp3CommandStr);
      }

      // Send servo command
      const servoCommand = this.commandBuilder.buildServoCommand(frame);
      await this.serialPort.sendCommand(servoCommand);
    } catch (error) {
      throw new SerialError(`Failed to execute frame: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Execute a sequence of frames
   */
  async executeSequence(frames: ActionFrame[], options: ExecutionOptions): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    if (this.executionState === 'running') {
      throw new Error('Sequence already executing');
    }

    try {
      this.executionState = 'running';
      const abortController = new AbortController();
      
      this.currentExecution = {
        frames,
        currentIndex: 0,
        options,
        abortController
      };

      do {
        for (let i = 0; i < frames.length; i++) {
          // Check if execution was stopped
          if (abortController.signal.aborted) {
            this.executionState = 'stopped';
            if (options.onComplete) {
              options.onComplete();
            }
            return;
          }

          this.currentExecution.currentIndex = i;
          const frame = frames[i];

          // Report progress
          if (options.onProgress) {
            const progress: ExecutionProgress = {
              currentFrame: i,
              totalFrames: frames.length,
              percentage: ((i + 1) / frames.length) * 100
            };
            options.onProgress(progress);
          }

          // Execute frame
          await this.executeFrame(frame);

          // Wait for frame duration
          await this.delay(frame.duration);
        }
      } while (options.loop && !abortController.signal.aborted);

      this.executionState = 'idle';
      this.currentExecution = null;

      if (options.onComplete) {
        options.onComplete();
      }
    } catch (error) {
      this.executionState = 'error';
      this.currentExecution = null;
      
      if (options.onError) {
        options.onError(error instanceof Error ? error : new Error(String(error)));
      }
      
      throw new SerialError(`Sequence execution failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Stop current execution
   */
  async stopExecution(): Promise<void> {
    if (this.currentExecution) {
      this.currentExecution.abortController.abort();
    }

    // Send DISARM command to Arduino
    if (this.serialPort.isPortConnected()) {
      await this.serialPort.sendDisarmCommand();
    }

    this.executionState = 'stopped';
    this.currentExecution = null;
  }

  /**
   * Get current execution state
   */
  getExecutionState(): ExecutionState {
    return this.executionState;
  }

  /**
   * Get current execution progress
   */
  getCurrentProgress(): ExecutionProgress | null {
    if (!this.currentExecution) {
      return null;
    }

    return {
      currentFrame: this.currentExecution.currentIndex,
      totalFrames: this.currentExecution.frames.length,
      percentage: ((this.currentExecution.currentIndex + 1) / this.currentExecution.frames.length) * 100
    };
  }

  // ==================== Batch Download Operations ====================

  /**
   * Download sequence to Arduino EEPROM
   */
  async downloadSequence(project: ActionProject, slotId: number, onProgress?: (progress: number) => void): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }

    try {
      // Build download command
      const downloadCommand = this.commandBuilder.buildDownloadCommand(slotId, project.frames);
      
      // Split into chunks (max 256 bytes per chunk)
      const chunks = this.commandBuilder.chunkData(downloadCommand, 256);
      
      // Send chunks with progress reporting
      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        
        // Send chunk with retry logic
        let retries = 0;
        const maxRetries = 3;
        
        while (retries < maxRetries) {
          try {
            await this.serialPort.sendCommandWithResponse(chunk, 5000);
            break; // Success
          } catch (error) {
            retries++;
            if (retries >= maxRetries) {
              throw new SerialError(`Failed to send chunk ${i + 1}/${chunks.length} after ${maxRetries} attempts`);
            }
            // Wait before retry
            await this.delay(500);
          }
        }

        // Report progress
        if (onProgress) {
          const progress = ((i + 1) / chunks.length) * 100;
          onProgress(progress);
        }
      }

      // Verify download
      const readCommand = this.commandBuilder.buildReadCommand(slotId);
      const response = await this.serialPort.sendCommandWithResponse(readCommand, 5000);
      
      // Parse and validate response
      // (In a real implementation, we would deserialize and compare)
      console.log('Download verification response:', response);
      
    } catch (error) {
      throw new SerialError(`Download failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Format Arduino storage slot
   */
  async formatSlot(slotId: number): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }

    try {
      const formatCommand = this.commandBuilder.buildFormatCommand(slotId);
      await this.serialPort.sendCommandWithResponse(formatCommand, 5000);
    } catch (error) {
      throw new SerialError(`Format failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Set slot to offline mode (auto-run on boot)
   */
  async setOfflineMode(slotId: number): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }

    try {
      const offlineCommand = this.commandBuilder.buildSetOfflineCommand(slotId);
      await this.serialPort.sendCommandWithResponse(offlineCommand, 5000);
    } catch (error) {
      throw new SerialError(`Set offline mode failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Read sequence from Arduino slot for verification
   */
  async readSequence(slotId: number): Promise<ActionFrame[]> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }

    try {
      const readCommand = this.commandBuilder.buildReadCommand(slotId);
      const response = await this.serialPort.sendCommandWithResponse(readCommand, 5000);
      
      // Parse response and deserialize frames
      // Expected format: DATA:<serialized_frames>:<checksum>
      const parts = response.split(':');
      if (parts.length !== 3 || parts[0] !== 'DATA') {
        throw new SerialError(`Invalid response format: ${response}`);
      }

      const serializedData = parts[1];
      const receivedChecksum = parts[2];

      // Validate checksum
      if (!this.commandBuilder.validateChecksum(serializedData, receivedChecksum)) {
        throw new SerialError('Checksum validation failed');
      }

      // Deserialize frames
      return this.commandBuilder.deserializeFrames(serializedData);
    } catch (error) {
      throw new SerialError(`Read sequence failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  // ==================== MP3 Commands ====================

  /**
   * Send MP3 command
   */
  async sendMp3Command(command: Mp3Command): Promise<void> {
    if (!this.serialPort.isPortConnected()) {
      throw new SerialError('Serial port not connected');
    }

    try {
      const mp3CommandStr = this.commandBuilder.buildMp3Command(command);
      await this.serialPort.sendCommand(mp3CommandStr);
    } catch (error) {
      throw new SerialError(`MP3 command failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  // ==================== Utility Methods ====================

  /**
   * Delay helper for async operations
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Close service and cleanup resources
   */
  async close(): Promise<void> {
    if (this.currentExecution) {
      await this.stopExecution();
    }
    
    if (this.serialPort.isPortConnected()) {
      await this.serialPort.disconnect();
    }
    
    this.db.close();
  }
}
