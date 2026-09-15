import fc from 'fast-check';
import { RoboticArmService } from '../main/robotic-arm-service';
import { SQLiteDatabase } from '../main/database';
import { SerialPortManager } from '../main/serial-port-manager';
import { ActionFrame } from '../shared/types';
import { ActionFrameFactory } from '../shared/factories';
import * as path from 'path';
import * as fs from 'fs';

// Feature: robotic-arm-sequencer, Property 6: Update Preserves Identity
// Validates: Requirements 4.3

describe('Update Preserves Identity Property Tests', () => {
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

  test('Updating a frame should preserve its sequenceId', async () => {
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
        fc.integer(0, 2), // Index to update (will be clamped)
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
        async (projectName, frameDataArray, updateIndex, newFrameData) => {
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

          // Get original frame sequenceId
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          
          const validUpdateIndex = Math.max(0, Math.min(updateIndex, frames.length - 1));
          const originalSequenceId = project!.frames[validUpdateIndex].sequenceId;

          // Update the frame
          const updatedFrame = ActionFrameFactory.create({
            sequenceId: 999, // Try to change it (should be ignored)
            ...newFrameData
          });
          
          await service.updateFrame(projectId, validUpdateIndex, updatedFrame);

          // Get updated project and verify sequenceId is preserved
          const updatedProject = await service.getProject(projectId);
          expect(updatedProject).not.toBeNull();
          expect(updatedProject!.frames[validUpdateIndex].sequenceId).toBe(originalSequenceId);
          
          // Verify other properties were updated (accounting for clamping)
          const clampedDuration = Math.max(500, Math.min(5000, newFrameData.duration));
          const clampedServos = {
            1: Math.max(500, Math.min(2500, newFrameData.servos[1])),
            2: Math.max(500, Math.min(2500, newFrameData.servos[2])),
            3: Math.max(500, Math.min(2500, newFrameData.servos[3])),
            4: Math.max(500, Math.min(2500, newFrameData.servos[4])),
            5: Math.max(500, Math.min(2500, newFrameData.servos[5])),
            6: Math.max(500, Math.min(2500, newFrameData.servos[6]))
          };
          const clampedSoundId = newFrameData.soundId ? 
            Math.max(1, Math.min(255, newFrameData.soundId)) : undefined;
          
          expect(updatedProject!.frames[validUpdateIndex].duration).toBe(clampedDuration);
          expect(updatedProject!.frames[validUpdateIndex].servos).toEqual(clampedServos);
          expect(updatedProject!.frames[validUpdateIndex].soundId).toBe(clampedSoundId);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Multiple updates should preserve sequenceId', async () => {
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

          // Store original sequenceIds
          const project = await service.getProject(projectId);
          expect(project).not.toBeNull();
          const originalSequenceIds = project!.frames.map(f => f.sequenceId);

          // Perform multiple updates
          for (let i = 0; i < Math.min(3, frames.length); i++) {
            const newFrameData = ActionFrameFactory.create({
              sequenceId: 999, // Try to change it
              duration: 1000 + i * 100,
              servos: {
                1: 1500,
                2: 1500,
                3: 1500,
                4: 1500,
                5: 1500,
                6: 1500
              }
            });
            
            await service.updateFrame(projectId, i, newFrameData);
          }

          // Verify all sequenceIds are preserved
          const updatedProject = await service.getProject(projectId);
          expect(updatedProject).not.toBeNull();
          const newSequenceIds = updatedProject!.frames.map(f => f.sequenceId);
          
          expect(newSequenceIds).toEqual(originalSequenceIds);
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Update after reorder should preserve new sequenceIds', async () => {
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
          { minLength: 4, maxLength: 8 }
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

          // Reorder frames (reverse order)
          const newOrder = frames.map((_, i) => frames.length - 1 - i);
          await service.reorderFrames(projectId, newOrder);

          // Get sequenceIds after reorder
          const reorderedProject = await service.getProject(projectId);
          expect(reorderedProject).not.toBeNull();
          const sequenceIdsAfterReorder = reorderedProject!.frames.map(f => f.sequenceId);

          // Update a frame
          const updateIndex = 0;
          const newFrameData = ActionFrameFactory.create({
            sequenceId: 999,
            duration: 2000,
            servos: {
              1: 1800,
              2: 1800,
              3: 1800,
              4: 1800,
              5: 1800,
              6: 1800
            }
          });
          
          await service.updateFrame(projectId, updateIndex, newFrameData);

          // Verify sequenceIds are still preserved
          const finalProject = await service.getProject(projectId);
          expect(finalProject).not.toBeNull();
          const finalSequenceIds = finalProject!.frames.map(f => f.sequenceId);
          
          expect(finalSequenceIds).toEqual(sequenceIdsAfterReorder);
        }
      ),
      { numRuns: 1000 }
    );
  });
});
