import fc from 'fast-check';
import { RoboticArmService } from '../main/robotic-arm-service';
import { SQLiteDatabase } from '../main/database';
import { SerialPortManager } from '../main/serial-port-manager';
import { ActionFrameFactory } from '../shared/factories';
import * as path from 'path';
import * as fs from 'fs';

// Feature: robotic-arm-sequencer, Property 7: Undo-Redo Inverse Operations
// Validates: Requirements 4.7

describe('Undo-Redo Inverse Operations Property Tests', () => {
  let service: RoboticArmService;
  let db: SQLiteDatabase;
  let serialPort: SerialPortManager;
  let testDbPath: string;

  beforeEach(() => {
    // Create temporary database for testing
    testDbPath = path.join(process.cwd(), 'test-data', `test-${Date.now()}.db`);
    const testDbDir = path.dirname(testDbPath);
    if (!fs.existsSync(testDbDir)) {
      fs.mkdirSync(testDbDir, { recursive: true });
    }

    db = new SQLiteDatabase(testDbPath);
    serialPort = new SerialPortManager();
    service = new RoboticArmService(db, serialPort);
  });

  afterEach(async () => {
    await service.close();
    
    // Clean up test database
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  // Helper to serialize project state for comparison
  function serializeProjectState(project: any): string {
    if (!project) return 'null';
    return JSON.stringify({
      name: project.name,
      frames: project.frames.map((f: any) => ({
        sequenceId: f.sequenceId,
        duration: f.duration,
        servos: f.servos,
        soundId: f.soundId
      }))
    });
  }

  test('Add frame then undo should restore original state', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0 && !/[<>:"/\\|?*\x00-\x1f]/.test(s)),
        fc.array(
          fc.record({
            duration: fc.integer(500, 5000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            }),
            soundId: fc.option(fc.integer(1, 255))
          }),
          { minLength: 2, maxLength: 5 }
        ),
        fc.record({
          duration: fc.integer(500, 5000),
          servos: fc.record({
            1: fc.integer(500, 2500),
            2: fc.integer(500, 2500),
            3: fc.integer(500, 2500),
            4: fc.integer(500, 2500),
            5: fc.integer(500, 2500),
            6: fc.integer(500, 2500)
          }),
          soundId: fc.option(fc.integer(1, 255))
        }),
        async (projectName, initialFrameData, newFrameData) => {
          // Create project with initial frames
          const initialFrames = initialFrameData.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const projectId = await service.createProject({
            name: projectName,
            frames: initialFrames,
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // Get initial state
          const initialProject = await service.getProject(projectId);
          const initialState = serializeProjectState(initialProject);

          // Add a frame
          const newFrame = ActionFrameFactory.create({
            sequenceId: 0,
            ...newFrameData
          });
          await service.addFrame(projectId, newFrame);

          // Undo
          await service.undo();

          // Get state after undo
          const afterUndoProject = await service.getProject(projectId);
          const afterUndoState = serializeProjectState(afterUndoProject);

          // State should be restored
          expect(afterUndoState).toBe(initialState);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Add frame, undo, then redo should restore added state', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0 && !/[<>:"/\\|?*\x00-\x1f]/.test(s)),
        fc.array(
          fc.record({
            duration: fc.integer(500, 5000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            }),
            soundId: fc.option(fc.integer(1, 255))
          }),
          { minLength: 2, maxLength: 5 }
        ),
        fc.record({
          duration: fc.integer(500, 5000),
          servos: fc.record({
            1: fc.integer(500, 2500),
            2: fc.integer(500, 2500),
            3: fc.integer(500, 2500),
            4: fc.integer(500, 2500),
            5: fc.integer(500, 2500),
            6: fc.integer(500, 2500)
          }),
          soundId: fc.option(fc.integer(1, 255))
        }),
        async (projectName, initialFrameData, newFrameData) => {
          // Create project
          const initialFrames = initialFrameData.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const projectId = await service.createProject({
            name: projectName,
            frames: initialFrames,
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // Add a frame
          const newFrame = ActionFrameFactory.create({
            sequenceId: 0,
            ...newFrameData
          });
          await service.addFrame(projectId, newFrame);

          // Get state after add
          const afterAddProject = await service.getProject(projectId);
          const afterAddState = serializeProjectState(afterAddProject);

          // Undo
          await service.undo();

          // Redo
          await service.redo();

          // Get state after redo
          const afterRedoProject = await service.getProject(projectId);
          const afterRedoState = serializeProjectState(afterRedoProject);

          // State should match after add
          expect(afterRedoState).toBe(afterAddState);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Delete frame then undo should restore deleted frame', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0 && !/[<>:"/\\|?*\x00-\x1f]/.test(s)),
        fc.array(
          fc.record({
            duration: fc.integer(500, 5000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            }),
            soundId: fc.option(fc.integer(1, 255))
          }),
          { minLength: 3, maxLength: 6 }
        ),
        async (projectName, frameData) => {
          // Create project
          const frames = frameData.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const projectId = await service.createProject({
            name: projectName,
            frames,
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // Get initial state
          const initialProject = await service.getProject(projectId);
          const initialState = serializeProjectState(initialProject);

          // Delete a frame
          await service.deleteFrame(projectId, 1);

          // Undo
          await service.undo();

          // Get state after undo
          const afterUndoProject = await service.getProject(projectId);
          const afterUndoState = serializeProjectState(afterUndoProject);

          // State should be restored
          expect(afterUndoState).toBe(initialState);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Update frame then undo should restore original values', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0 && !/[<>:"/\\|?*\x00-\x1f]/.test(s)),
        fc.array(
          fc.record({
            duration: fc.integer(500, 5000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            }),
            soundId: fc.option(fc.integer(1, 255))
          }),
          { minLength: 2, maxLength: 5 }
        ),
        fc.record({
          duration: fc.integer(500, 5000),
          servos: fc.record({
            1: fc.integer(500, 2500),
            2: fc.integer(500, 2500),
            3: fc.integer(500, 2500),
            4: fc.integer(500, 2500),
            5: fc.integer(500, 2500),
            6: fc.integer(500, 2500)
          }),
          soundId: fc.option(fc.integer(1, 255))
        }),
        async (projectName, initialFrameData, updateData) => {
          // Create project
          const frames = initialFrameData.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const projectId = await service.createProject({
            name: projectName,
            frames,
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // Get initial state
          const initialProject = await service.getProject(projectId);
          const initialState = serializeProjectState(initialProject);

          // Update a frame
          const updatedFrame = ActionFrameFactory.create({
            sequenceId: 0,
            ...updateData
          });
          await service.updateFrame(projectId, 0, updatedFrame);

          // Undo
          await service.undo();

          // Get state after undo
          const afterUndoProject = await service.getProject(projectId);
          const afterUndoState = serializeProjectState(afterUndoProject);

          // State should be restored
          expect(afterUndoState).toBe(initialState);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Multiple operations with undo/redo should maintain consistency', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0 && !/[<>:"/\\|?*\x00-\x1f]/.test(s)),
        fc.array(
          fc.record({
            duration: fc.integer(500, 5000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            }),
            soundId: fc.option(fc.integer(1, 255))
          }),
          { minLength: 3, maxLength: 5 }
        ),
        async (projectName, frameData) => {
          // Create project
          const frames = frameData.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const projectId = await service.createProject({
            name: projectName,
            frames,
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // State 0: Initial
          const state0 = serializeProjectState(await service.getProject(projectId));

          // Operation 1: Add frame
          const newFrame1 = ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          });
          await service.addFrame(projectId, newFrame1);
          const state1 = serializeProjectState(await service.getProject(projectId));

          // Operation 2: Delete frame
          await service.deleteFrame(projectId, 0);
          const state2 = serializeProjectState(await service.getProject(projectId));

          // Undo operation 2 -> should be at state 1
          await service.undo();
          expect(serializeProjectState(await service.getProject(projectId))).toBe(state1);

          // Undo operation 1 -> should be at state 0
          await service.undo();
          expect(serializeProjectState(await service.getProject(projectId))).toBe(state0);

          // Redo operation 1 -> should be at state 1
          await service.redo();
          expect(serializeProjectState(await service.getProject(projectId))).toBe(state1);

          // Redo operation 2 -> should be at state 2
          await service.redo();
          expect(serializeProjectState(await service.getProject(projectId))).toBe(state2);
        }
      ),
      { numRuns: 1000 }
    );
  });
});
