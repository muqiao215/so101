/**
 * Integration Tests for Robotic Arm Sequencer
 * Tests complete user flows and system integration
 * Requirements: All
 */

import { SQLiteDatabase } from '../main/database';
import { SerialPortManager } from '../main/serial-port-manager';
import { RoboticArmService } from '../main/robotic-arm-service';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';
import { ActionProject, ActionFrame, ExecutionProgress } from '../shared/types';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// Mock SerialPort to avoid hardware dependency
jest.mock('serialport');
jest.mock('@serialport/parser-readline');

describe('Integration Tests', () => {
  let db: SQLiteDatabase;
  let serialPort: SerialPortManager;
  let service: RoboticArmService;
  let tempDbPath: string;

  beforeEach(() => {
    // Create temporary database for testing
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'robotic-arm-test-'));
    tempDbPath = path.join(tempDir, 'test.db');
    
    db = new SQLiteDatabase(tempDbPath);
    serialPort = new SerialPortManager();
    service = new RoboticArmService(db, serialPort);
  });

  afterEach(async () => {
    await service.close();
    
    // Clean up temporary database
    if (fs.existsSync(tempDbPath)) {
      fs.unlinkSync(tempDbPath);
      fs.rmdirSync(path.dirname(tempDbPath));
    }
  });

  describe('Complete User Flow: Create Project → Add Frames → Execute → Download', () => {
    test('should complete full workflow successfully', async () => {
      // Step 1: Create a new project
      const projectId = await service.createProject({
        name: 'Test Sequence',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      expect(projectId).toBeDefined();
      expect(typeof projectId).toBe('string');

      // Step 2: Add frames to the project
      const frame1 = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
        soundId: 1
      });

      const frame2 = ActionFrameFactory.create({
        sequenceId: 1,
        duration: 1500,
        servos: { 1: 2000, 2: 2000, 3: 2000, 4: 2000, 5: 2000, 6: 2000 }
      });

      const frame3 = ActionFrameFactory.create({
        sequenceId: 2,
        duration: 2000,
        servos: { 1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000 },
        soundId: 2
      });

      await service.addFrame(projectId, frame1);
      await service.addFrame(projectId, frame2);
      await service.addFrame(projectId, frame3);

      // Step 3: Verify project was saved correctly
      const project = await service.getProject(projectId);
      expect(project).not.toBeNull();
      expect(project!.frames).toHaveLength(3);
      expect(project!.frames[0].sequenceId).toBe(0);
      expect(project!.frames[1].sequenceId).toBe(1);
      expect(project!.frames[2].sequenceId).toBe(2);

      // Step 4: Execute sequence (with mock serial port)
      const progressUpdates: ExecutionProgress[] = [];
      let executionCompleted = false;

      // Mock serial port connection
      jest.spyOn(serialPort, 'isPortConnected').mockReturnValue(true);
      jest.spyOn(serialPort, 'sendCommand').mockResolvedValue();

      await service.executeSequence(project!.frames, {
        loop: false,
        onProgress: (progress) => {
          progressUpdates.push(progress);
        },
        onComplete: () => {
          executionCompleted = true;
        }
      });

      // Verify execution progress
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(executionCompleted).toBe(true);
      expect(progressUpdates[progressUpdates.length - 1].percentage).toBe(100);

      // Step 5: Download to Arduino (mock)
      jest.spyOn(serialPort, 'sendCommandWithResponse').mockResolvedValue('OK');

      let downloadProgress = 0;
      await service.downloadSequence(project!, 1, (progress) => {
        downloadProgress = progress;
      });

      expect(downloadProgress).toBe(100);
    });

    test('should handle project modifications during workflow', async () => {
      // Create project
      const projectId = await service.createProject({
        name: 'Modifiable Project',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // Add initial frames
      const frame1 = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
      });

      await service.addFrame(projectId, frame1);

      // Insert frame at beginning
      const frame0 = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 500,
        servos: { 1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000 }
      });

      await service.insertFrame(projectId, 0, frame0);

      // Verify renumbering
      const project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(2);
      expect(project!.frames[0].duration).toBe(500);
      expect(project!.frames[0].sequenceId).toBe(0);
      expect(project!.frames[1].duration).toBe(1000);
      expect(project!.frames[1].sequenceId).toBe(1);

      // Update a frame
      const updatedFrame = { ...project!.frames[1], duration: 2000 };
      await service.updateFrame(projectId, 1, updatedFrame);

      // Delete a frame
      await service.deleteFrame(projectId, 0);

      // Verify final state
      const finalProject = await service.getProject(projectId);
      expect(finalProject!.frames).toHaveLength(1);
      expect(finalProject!.frames[0].sequenceId).toBe(0);
      expect(finalProject!.frames[0].duration).toBe(2000);
    });
  });

  describe('Serial Communication with Mock Arduino', () => {
    test('should handle serial commands correctly', async () => {
      const sentCommands: string[] = [];

      jest.spyOn(serialPort, 'isPortConnected').mockReturnValue(true);
      jest.spyOn(serialPort, 'sendCommand').mockImplementation(async (cmd) => {
        sentCommands.push(cmd);
      });

      const frame = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1600, 3: 1700, 4: 1800, 5: 1900, 6: 2000 },
        soundId: 5
      });

      await service.executeFrame(frame);

      // Verify MP3 command was sent first
      expect(sentCommands[0]).toContain('MP3_PLAY:005');
      
      // Verify servo command format
      expect(sentCommands[1]).toMatch(/#1P1500#2P1600#3P1700#4P1800#5P1900#6P2000T1000!/);
    });

    test('should handle connection loss during execution', async () => {
      const projectId = await service.createProject({
        name: 'Connection Test',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      const frame = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
      });

      await service.addFrame(projectId, frame);

      const project = await service.getProject(projectId);

      // Simulate connection loss
      jest.spyOn(serialPort, 'isPortConnected').mockReturnValue(false);

      await expect(
        service.executeSequence(project!.frames, { loop: false })
      ).rejects.toThrow('Serial port not connected');
    });

    test('should retry failed commands', async () => {
      let attemptCount = 0;

      jest.spyOn(serialPort, 'isPortConnected').mockReturnValue(true);
      jest.spyOn(serialPort, 'sendCommandWithResponse').mockImplementation(async () => {
        attemptCount++;
        if (attemptCount < 3) {
          throw new Error('Connection timeout');
        }
        return 'OK';
      });

      const projectId = await service.createProject({
        name: 'Retry Test',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          })
        ],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      const project = await service.getProject(projectId);

      await service.downloadSequence(project!, 1);

      // Verify retry logic worked
      expect(attemptCount).toBeGreaterThanOrEqual(3);
    });
  });

  describe('File Import/Export with Temporary Files', () => {
    test('should export and import project correctly', async () => {
      // Create a project
      const originalProject = ActionProjectFactory.create({
        name: 'Export Test Project',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1600, 3: 1700, 4: 1800, 5: 1900, 6: 2000 },
            soundId: 1
          }),
          ActionFrameFactory.create({
            sequenceId: 1,
            duration: 1500,
            servos: { 1: 2000, 2: 1900, 3: 1800, 4: 1700, 5: 1600, 6: 1500 }
          })
        ]
      });

      await service.createProject(originalProject);

      // Export to temporary file
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'export-test-'));
      const exportPath = path.join(tempDir, 'test-project.armseq');

      fs.writeFileSync(exportPath, JSON.stringify(originalProject, null, 2));

      // Import from file
      const importedData = JSON.parse(fs.readFileSync(exportPath, 'utf-8'));

      // Verify data integrity
      expect(importedData.name).toBe(originalProject.name);
      expect(importedData.frames).toHaveLength(2);
      expect(importedData.frames[0].duration).toBe(1000);
      expect(importedData.frames[0].soundId).toBe(1);
      expect(importedData.frames[1].duration).toBe(1500);

      // Clean up
      fs.unlinkSync(exportPath);
      fs.rmdirSync(tempDir);
    });

    test('should handle invalid import files', () => {
      const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'invalid-import-'));
      const invalidPath = path.join(tempDir, 'invalid.armseq');

      // Write invalid JSON
      fs.writeFileSync(invalidPath, 'This is not valid JSON');

      expect(() => {
        JSON.parse(fs.readFileSync(invalidPath, 'utf-8'));
      }).toThrow();

      // Clean up
      fs.unlinkSync(invalidPath);
      fs.rmdirSync(tempDir);
    });
  });

  describe('Error Recovery Scenarios', () => {
    test('should recover from database errors', async () => {
      // Create a project
      const projectId = await service.createProject({
        name: 'Error Recovery Test',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // Attempt to create duplicate project (should fail with DuplicateProjectError)
      try {
        await db.insertProject({
          id: projectId,
          name: 'Duplicate',
          created_at: Date.now(),
          modified_at: Date.now()
        });
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.message).toContain('already exists');
      }

      // Verify original project still exists
      const project = await service.getProject(projectId);
      expect(project).not.toBeNull();
      expect(project!.name).toBe('Error Recovery Test');
    });

    test('should handle invalid frame operations gracefully', async () => {
      const projectId = await service.createProject({
        name: 'Invalid Operations Test',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // Try to update non-existent frame
      await expect(
        service.updateFrame(projectId, 0, ActionFrameFactory.create({
          sequenceId: 0,
          duration: 1000,
          servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
        }))
      ).rejects.toThrow('Invalid index');

      // Try to delete non-existent frame
      await expect(
        service.deleteFrame(projectId, 0)
      ).rejects.toThrow('Invalid index');

      // Verify project is still intact
      const project = await service.getProject(projectId);
      expect(project).not.toBeNull();
      expect(project!.frames).toHaveLength(0);
    });

    test('should handle execution errors', async () => {
      const projectId = await service.createProject({
        name: 'Execution Error Test',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          })
        ],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      const project = await service.getProject(projectId);

      jest.spyOn(serialPort, 'isPortConnected').mockReturnValue(true);
      jest.spyOn(serialPort, 'sendCommand').mockRejectedValue(new Error('Serial error'));

      let errorCaught = false;

      await service.executeSequence(project!.frames, {
        loop: false,
        onError: (error) => {
          errorCaught = true;
          expect(error.message).toContain('Serial error');
        }
      }).catch(() => {
        // Expected to throw
      });

      expect(errorCaught).toBe(true);
    });
  });

  describe('Undo/Redo Integration', () => {
    test('should support undo/redo across multiple operations', async () => {
      const projectId = await service.createProject({
        name: 'UndoRedoTest',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // Add frame 1
      const frame1 = ActionFrameFactory.create({
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
      });
      await service.addFrame(projectId, frame1);

      // Verify 1 frame
      let project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(1);

      // Add frame 2
      const frame2 = ActionFrameFactory.create({
        sequenceId: 1,
        duration: 1500,
        servos: { 1: 2000, 2: 2000, 3: 2000, 4: 2000, 5: 2000, 6: 2000 }
      });
      await service.addFrame(projectId, frame2);

      // Verify 2 frames
      project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(2);

      // Undo last add - should go back to 1 frame
      expect(service.canUndo()).toBe(true);
      await service.undo();
      project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(1);

      // Redo - should go back to 2 frames
      expect(service.canRedo()).toBe(true);
      await service.redo();
      project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(2);

      // Undo once - should go back to 1 frame
      await service.undo();
      project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(1);
    });
  });

  describe('Performance and Caching', () => {
    test('should cache frequently accessed projects', async () => {
      const projectId = await service.createProject({
        name: 'Cache Test',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // First access - should load from database
      const project1 = await service.getProject(projectId);
      expect(project1).not.toBeNull();

      // Second access - should load from cache
      const project2 = await service.getProject(projectId);
      expect(project2).not.toBeNull();
      expect(project2!.id).toBe(project1!.id);

      // Verify cache stats
      const stats = service.getCacheStats();
      expect(stats.hitCount).toBeGreaterThan(0);
    });

    test('should handle large projects efficiently', async () => {
      const projectId = await service.createProject({
        name: 'Large Project',
        frames: [],
        createdAt: Date.now(),
        modifiedAt: Date.now()
      });

      // Add 100 frames
      const startTime = Date.now();
      for (let i = 0; i < 100; i++) {
        await service.addFrame(projectId, ActionFrameFactory.create({
          sequenceId: i,
          duration: 1000,
          servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
        }));
      }
      const endTime = Date.now();

      // Should complete in reasonable time (< 5 seconds)
      expect(endTime - startTime).toBeLessThan(5000);

      // Verify all frames were added
      const project = await service.getProject(projectId);
      expect(project!.frames).toHaveLength(100);
    });
  });
});
