import fc from 'fast-check';
import { RoboticArmService } from '../main/robotic-arm-service';
import { SQLiteDatabase } from '../main/database';
import { SerialPortManager } from '../main/serial-port-manager';
import { ActionFrame, ActionProject } from '../shared/types';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';
import * as path from 'path';
import * as fs from 'fs';

// Feature: robotic-arm-sequencer, Property 5: Frame List Operations Preserve Invariants
// Validates: Requirements 4.1, 4.2, 4.4, 4.5

describe('Frame List Operations Property Tests', () => {
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

  // Helper to check frame list invariants
  function checkFrameInvariants(frames: ActionFrame[]): boolean {
    if (frames.length === 0) return true;

    // Check 1: All sequenceIds are consecutive integers starting from 0
    for (let i = 0; i < frames.length; i++) {
      if (frames[i].sequenceId !== i) {
        return false;
      }
    }

    // Check 2: List order matches sequenceId order
    for (let i = 1; i < frames.length; i++) {
      if (frames[i].sequenceId <= frames[i - 1].sequenceId) {
        return false;
      }
    }

    // Check 3: No duplicate sequenceIds
    const sequenceIds = frames.map(f => f.sequenceId);
    const uniqueIds = new Set(sequenceIds);
    if (uniqueIds.size !== sequenceIds.length) {
      return false;
    }

    // Check 4: Frame count equals number of unique sequenceIds
    if (frames.length !== uniqueIds.size) {
      return false;
    }

    return true;
  }

  test('Adding frames should preserve invariants', async () => {
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
          { minLength: 1, maxLength: 20 }
        ),
        async (projectName, frameDataArray) => {
          // Create project
          const projectId = await service.createProject({
            name: projectName,
            frames: [],
            createdAt: Date.now(),
            modifiedAt: Date.now()
          });

          // Add frames one by one
          for (const frameData of frameDataArray) {
            const frame = ActionFrameFactory.create({
              sequenceId: 0, // Will be set by service
              ...frameData
            });
            await service.addFrame(projectId, frame);
          }

          // Get project and check invariants
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          expect(checkFrameInvariants(project!.frames)).toBe(true);
          expect(project!.frames.length).toBe(frameDataArray.length);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Inserting frames should preserve invariants', async () => {
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
          { minLength: 3, maxLength: 10 }
        ),
        fc.integer(0, 2), // Insert position (will be clamped to valid range)
        async (projectName, frameDataArray, insertPos) => {
          // Create project with initial frames
          const initialFrames = frameDataArray.slice(0, -1).map((data, i) =>
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

          // Insert a new frame at position
          const newFrameData = frameDataArray[frameDataArray.length - 1];
          const newFrame = ActionFrameFactory.create({
            sequenceId: 0, // Will be set by service
            ...newFrameData
          });

          const validInsertPos = Math.max(0, Math.min(insertPos, initialFrames.length));
          await service.insertFrame(projectId, validInsertPos, newFrame);

          // Get project and check invariants
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          expect(checkFrameInvariants(project!.frames)).toBe(true);
          expect(project!.frames.length).toBe(frameDataArray.length);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Deleting frames should preserve invariants', async () => {
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
          { minLength: 2, maxLength: 10 }
        ),
        async (projectName, frameDataArray) => {
          // Create project with frames
          const frames = frameDataArray.map((data, i) =>
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

          // Delete a frame (always delete the first one for consistency)
          await service.deleteFrame(projectId, 0);

          // Get project and check invariants
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          expect(checkFrameInvariants(project!.frames)).toBe(true);
          expect(project!.frames.length).toBe(frameDataArray.length - 1);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Reordering frames should preserve invariants', async () => {
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
          { minLength: 3, maxLength: 10 }
        ),
        async (projectName, frameDataArray) => {
          // Create project with frames
          const frames = frameDataArray.map((data, i) =>
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

          // Generate a random valid reordering
          const newOrder = frames.map((_, i) => i);
          // Shuffle using Fisher-Yates algorithm
          for (let i = newOrder.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newOrder[i], newOrder[j]] = [newOrder[j], newOrder[i]];
          }

          await service.reorderFrames(projectId, newOrder);

          // Get project and check invariants
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          expect(checkFrameInvariants(project!.frames)).toBe(true);
          expect(project!.frames.length).toBe(frameDataArray.length);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Mixed operations should preserve invariants', async () => {
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
          { minLength: 5, maxLength: 10 }
        ),
        async (projectName, frameDataArray) => {
          // Create project with initial frames
          const initialFrames = frameDataArray.slice(0, 3).map((data, i) =>
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

          // Perform mixed operations
          // Add a frame
          const newFrame1 = ActionFrameFactory.create({
            sequenceId: 0,
            ...frameDataArray[3]
          });
          await service.addFrame(projectId, newFrame1);

          // Insert a frame
          const newFrame2 = ActionFrameFactory.create({
            sequenceId: 0,
            ...frameDataArray[4]
          });
          await service.insertFrame(projectId, 1, newFrame2);

          // Delete a frame
          await service.deleteFrame(projectId, 2);

          // Check invariants after each operation
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          expect(checkFrameInvariants(project!.frames)).toBe(true);
        }
      ),
      { numRuns: 1000 }
    );
  });
});
