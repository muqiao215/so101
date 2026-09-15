/**
 * IPC Client Wrapper for Renderer Process
 * Provides a convenient interface for communicating with the main process
 * Includes error handling and type safety
 */

import type {
  ActionProject,
  ActionFrame,
  ExecutionOptions,
  ExecutionProgress,
  ExecutionState,
  Mp3Command,
  PortInfo
} from '../shared/types';

// Check if running in Electron environment
const isElectronEnv = typeof window !== 'undefined' && window.electronAPI !== undefined;

// Log warning if not in Electron environment
if (!isElectronEnv) {
  console.warn('⚠️ electronAPI not available - running in fallback/demo mode');
}

const createDemoProjectId = () => `demo-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

let demoProjects: ActionProject[] = [];

const findDemoProjectIndex = (projectId: string) =>
  demoProjects.findIndex((project) => project.id === projectId);

const renumberDemoFrames = (frames: ActionFrame[]) =>
  frames.map((frame, index) => ({
    ...frame,
    sequenceId: index,
  }));

const updateDemoProject = (projectId: string, updater: (project: ActionProject) => ActionProject) => {
  const projectIndex = findDemoProjectIndex(projectId);
  if (projectIndex === -1) {
    throw new Error(`Project not found: ${projectId}`);
  }

  const currentProject = demoProjects[projectIndex];
  const nextProject = updater(currentProject);
  demoProjects = demoProjects.map((project, index) =>
    index === projectIndex ? nextProject : project
  );
};

/**
 * Mock API for when electronAPI is not available (e.g., in browser dev mode)
 */
const mockAPI = {
  getVersion: async () => '1.0.0-demo',
  getTheme: async () => ({ shouldUseDarkColors: true, shouldUseHighContrastColors: false, shouldUseInvertedColorScheme: false }),
  updateTrayStatus: async () => { },
  on: {
    themeChanged: () => { },
    fileOpened: () => { },
    menuNewProject: () => { },
    menuSaveProject: () => { },
    menuSaveProjectAs: () => { },
    menuImportProject: () => { },
    menuExportProject: () => { },
    menuUndo: () => { },
    menuRedo: () => { },
  },
  project: {
    create: async (project: Omit<ActionProject, 'id'>) => {
      const createdProject: ActionProject = {
        ...project,
        id: createDemoProjectId(),
      };

      demoProjects = [createdProject, ...demoProjects];
      return createdProject.id;
    },
    get: async (id: string) => demoProjects.find((project) => project.id === id) ?? null,
    getAll: async () => [...demoProjects],
    update: async (project: ActionProject) => {
      demoProjects = demoProjects.map((currentProject) =>
        currentProject.id === project.id ? { ...project } : currentProject
      );
    },
    delete: async (id: string) => {
      demoProjects = demoProjects.filter((project) => project.id !== id);
    },
  },
  frame: {
    add: async (projectId: string, frame: ActionFrame) => {
      updateDemoProject(projectId, (project) => ({
        ...project,
        frames: renumberDemoFrames([...project.frames, frame]),
        modifiedAt: Date.now(),
      }));
    },
    insert: async (projectId: string, index: number, frame: ActionFrame) => {
      updateDemoProject(projectId, (project) => {
        const frames = [...project.frames];
        const insertIndex = Math.max(0, Math.min(index, frames.length));
        frames.splice(insertIndex, 0, frame);

        return {
          ...project,
          frames: renumberDemoFrames(frames),
          modifiedAt: Date.now(),
        };
      });
    },
    update: async (projectId: string, index: number, frame: ActionFrame) => {
      updateDemoProject(projectId, (project) => {
        if (index < 0 || index >= project.frames.length) {
          throw new Error(`Frame index out of range: ${index}`);
        }

        const frames = [...project.frames];
        frames[index] = {
          ...frame,
          sequenceId: index,
        };

        return {
          ...project,
          frames,
          modifiedAt: Date.now(),
        };
      });
    },
    delete: async (projectId: string, index: number) => {
      updateDemoProject(projectId, (project) => {
        if (index < 0 || index >= project.frames.length) {
          throw new Error(`Frame index out of range: ${index}`);
        }

        const frames = [...project.frames];
        frames.splice(index, 1);

        return {
          ...project,
          frames: renumberDemoFrames(frames),
          modifiedAt: Date.now(),
        };
      });
    },
    reorder: async (projectId: string, newOrder: number[]) => {
      updateDemoProject(projectId, (project) => {
        if (newOrder.length !== project.frames.length) {
          throw new Error('Invalid frame reorder payload');
        }

        const frames = newOrder.map((frameIndex) => {
          if (frameIndex < 0 || frameIndex >= project.frames.length) {
            throw new Error(`Frame index out of range: ${frameIndex}`);
          }

          return project.frames[frameIndex];
        });

        return {
          ...project,
          frames: renumberDemoFrames(frames),
          modifiedAt: Date.now(),
        };
      });
    },
  },
  edit: {
    undo: async () => { },
    redo: async () => { },
    canUndo: async () => false,
    canRedo: async () => false,
  },
  serial: {
    connect: async (_portPath: string, _baudRate: number) => { },
    disconnect: async () => { },
    listPorts: async () => [] as PortInfo[],
    isConnected: async () => false,
    executeFrame: async () => { },
    executeSequence: async () => { },
    stopExecution: async () => { },
    getExecutionState: async () => 'idle' as ExecutionState,
    getCurrentProgress: async () => null,
    sendRawCommand: async (_command: string) => { },
  },
  download: {
    sequence: async () => { },
    formatSlot: async () => { },
    setOfflineMode: async () => { },
    readSequence: async () => [] as ActionFrame[],
  },
  mp3: {
    sendCommand: async () => { },
  },
  file: {
    export: async () => null,
    import: async () => { throw new Error('Not available in demo mode'); },
    showSaveDialog: async () => null,
    showOpenDialog: async () => null,
  },
};

/**
 * IPC Client for renderer process
 * Wraps window.electronAPI with additional error handling and convenience methods
 */
export class IPCClient {
  private api = isElectronEnv ? window.electronAPI : mockAPI;
  public isDemo = !isElectronEnv;


  async getVersion(): Promise<string> {
    try {
      return await this.api.getVersion();
    } catch (error) {
      throw this.handleError('Failed to get app version', error);
    }
  }

  // ==================== Project Operations ====================

  async createProject(project: Omit<ActionProject, 'id'>): Promise<string> {
    try {
      return await this.api.project.create(project);
    } catch (error) {
      throw this.handleError('Failed to create project', error);
    }
  }

  async getProject(id: string): Promise<ActionProject | null> {
    try {
      return await this.api.project.get(id);
    } catch (error) {
      throw this.handleError(`Failed to get project ${id}`, error);
    }
  }

  async getAllProjects(): Promise<ActionProject[]> {
    try {
      return await this.api.project.getAll();
    } catch (error) {
      throw this.handleError('Failed to get all projects', error);
    }
  }

  async updateProject(project: ActionProject): Promise<void> {
    try {
      await this.api.project.update(project);
    } catch (error) {
      throw this.handleError(`Failed to update project ${project.id}`, error);
    }
  }

  async deleteProject(id: string): Promise<void> {
    try {
      await this.api.project.delete(id);
    } catch (error) {
      throw this.handleError(`Failed to delete project ${id}`, error);
    }
  }

  // ==================== Frame Operations ====================

  async addFrame(projectId: string, frame: ActionFrame): Promise<void> {
    try {
      await this.api.frame.add(projectId, frame);
    } catch (error) {
      throw this.handleError('Failed to add frame', error);
    }
  }

  async insertFrame(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    try {
      await this.api.frame.insert(projectId, index, frame);
    } catch (error) {
      throw this.handleError(`Failed to insert frame at index ${index}`, error);
    }
  }

  async updateFrame(projectId: string, index: number, frame: ActionFrame): Promise<void> {
    try {
      await this.api.frame.update(projectId, index, frame);
    } catch (error) {
      throw this.handleError(`Failed to update frame at index ${index}`, error);
    }
  }

  async deleteFrame(projectId: string, index: number): Promise<void> {
    try {
      await this.api.frame.delete(projectId, index);
    } catch (error) {
      throw this.handleError(`Failed to delete frame at index ${index}`, error);
    }
  }

  async reorderFrames(projectId: string, newOrder: number[]): Promise<void> {
    try {
      await this.api.frame.reorder(projectId, newOrder);
    } catch (error) {
      throw this.handleError('Failed to reorder frames', error);
    }
  }

  // ==================== Undo/Redo Operations ====================

  async undo(): Promise<void> {
    try {
      await this.api.edit.undo();
    } catch (error) {
      throw this.handleError('Failed to undo', error);
    }
  }

  async redo(): Promise<void> {
    try {
      await this.api.edit.redo();
    } catch (error) {
      throw this.handleError('Failed to redo', error);
    }
  }

  async canUndo(): Promise<boolean> {
    try {
      return await this.api.edit.canUndo();
    } catch (error) {
      throw this.handleError('Failed to check undo availability', error);
    }
  }

  async canRedo(): Promise<boolean> {
    try {
      return await this.api.edit.canRedo();
    } catch (error) {
      throw this.handleError('Failed to check redo availability', error);
    }
  }

  // ==================== Serial Communication ====================

  async connectSerial(portPath: string, baudRate: number): Promise<void> {
    try {
      await this.api.serial.connect(portPath, baudRate);
    } catch (error) {
      throw this.handleError(`Failed to connect to serial port ${portPath} at ${baudRate} baud`, error);
    }
  }

  async disconnectSerial(): Promise<void> {
    try {
      await this.api.serial.disconnect();
    } catch (error) {
      throw this.handleError('Failed to disconnect serial port', error);
    }
  }

  async listSerialPorts(): Promise<PortInfo[]> {
    try {
      return await this.api.serial.listPorts();
    } catch (error) {
      throw this.handleError('Failed to list serial ports', error);
    }
  }

  async isSerialConnected(): Promise<boolean> {
    try {
      return await this.api.serial.isConnected();
    } catch (error) {
      throw this.handleError('Failed to check serial connection status', error);
    }
  }

  async executeFrame(frame: ActionFrame): Promise<void> {
    try {
      await this.api.serial.executeFrame(frame);
    } catch (error) {
      throw this.handleError('Failed to execute frame', error);
    }
  }

  async executeSequence(frames: ActionFrame[], options: ExecutionOptions): Promise<void> {
    try {
      await this.api.serial.executeSequence(frames, options);
    } catch (error) {
      throw this.handleError('Failed to execute sequence', error);
    }
  }

  async stopExecution(): Promise<void> {
    try {
      await this.api.serial.stopExecution();
    } catch (error) {
      throw this.handleError('Failed to stop execution', error);
    }
  }

  async getExecutionState(): Promise<ExecutionState> {
    try {
      return await this.api.serial.getExecutionState();
    } catch (error) {
      throw this.handleError('Failed to get execution state', error);
    }
  }

  async getCurrentProgress(): Promise<ExecutionProgress | null> {
    try {
      return await this.api.serial.getCurrentProgress();
    } catch (error) {
      throw this.handleError('Failed to get current progress', error);
    }
  }

  // Send raw command to Arduino (CENTER, ARM, DISARM, etc.)
  async sendRawCommand(command: string): Promise<void> {
    try {
      // Use type assertion since sendRawCommand may not be in all API types
      const serial = this.api.serial as any;
      if (serial?.sendRawCommand) {
        await serial.sendRawCommand(command);
      }
    } catch (error) {
      throw this.handleError(`Failed to send command: ${command}`, error);
    }
  }

  // Convenience method to center all servos
  async centerServos(): Promise<void> {
    try {
      await this.sendRawCommand('CENTER');
    } catch (error) {
      throw this.handleError('Failed to center servos', error);
    }
  }

  // ==================== Batch Download Operations ====================

  async downloadSequence(
    project: ActionProject,
    slotId: number,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    try {
      await this.api.download.sequence(project, slotId, onProgress);
    } catch (error) {
      throw this.handleError(`Failed to download sequence to slot ${slotId}`, error);
    }
  }

  async formatSlot(slotId: number): Promise<void> {
    try {
      await this.api.download.formatSlot(slotId);
    } catch (error) {
      throw this.handleError(`Failed to format slot ${slotId}`, error);
    }
  }

  async setOfflineMode(slotId: number): Promise<void> {
    try {
      await this.api.download.setOfflineMode(slotId);
    } catch (error) {
      throw this.handleError(`Failed to set offline mode for slot ${slotId}`, error);
    }
  }

  async readSequence(slotId: number): Promise<ActionFrame[]> {
    try {
      return await this.api.download.readSequence(slotId);
    } catch (error) {
      throw this.handleError(`Failed to read sequence from slot ${slotId}`, error);
    }
  }

  // ==================== MP3 Commands ====================

  async sendMp3Command(command: Mp3Command): Promise<void> {
    try {
      await this.api.mp3.sendCommand(command);
    } catch (error) {
      throw this.handleError(`Failed to send MP3 command: ${command.type}`, error);
    }
  }

  // Convenience methods for MP3 commands
  async playMp3(trackId: number): Promise<void> {
    return this.sendMp3Command({ type: 'play', trackId });
  }

  async stopMp3(): Promise<void> {
    return this.sendMp3Command({ type: 'stop' });
  }

  async nextMp3(): Promise<void> {
    return this.sendMp3Command({ type: 'next' });
  }

  async previousMp3(): Promise<void> {
    return this.sendMp3Command({ type: 'previous' });
  }

  async setMp3Volume(level: number): Promise<void> {
    return this.sendMp3Command({ type: 'volume', level });
  }

  // ==================== File Operations ====================

  async exportProject(project: ActionProject): Promise<string | null> {
    try {
      return await this.api.file.export(project);
    } catch (error) {
      throw this.handleError('Failed to export project', error);
    }
  }

  async importProject(filePath: string): Promise<ActionProject> {
    try {
      return await this.api.file.import(filePath);
    } catch (error) {
      throw this.handleError('Failed to import project', error);
    }
  }

  async showSaveDialog(defaultName: string): Promise<string | null> {
    try {
      return await this.api.file.showSaveDialog(defaultName);
    } catch (error) {
      throw this.handleError('Failed to show save dialog', error);
    }
  }

  async showOpenDialog(): Promise<string | null> {
    try {
      return await this.api.file.showOpenDialog();
    } catch (error) {
      throw this.handleError('Failed to show open dialog', error);
    }
  }

  // ==================== Error Handling ====================

  private handleError(message: string, error: unknown): Error {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`${message}:`, error);
    return new Error(`${message}: ${errorMessage}`);
  }
}

// Export singleton instance
export const ipcClient = new IPCClient();
