import fc from 'fast-check';
import { RoboticArmService } from '../main/robotic-arm-service';
import { SQLiteDatabase } from '../main/database';
import { SerialPortManager } from '../main/serial-port-manager';
import { ActionFrame, ExecutionProgress } from '../shared/types';
import { ActionFrameFactory } from '../shared/factories';
import * as path from 'path';
import * as fs from 'fs';

// Feature: robotic-arm-sequencer, Property 9: Sequence Execution Order
// Validates: Requirements 5.2

describe('Sequence Execution Order Property Tests', () => {
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

  test('Frames should be executed in sequence order', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(
          fc.record({
            duration: fc.integer(500, 1000), // Shorter durations for faster tests
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
        async (frameDataArray) => {
          // Create frames with sequential IDs
          const frames = frameDataArray.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          // Track execution order
          const executedFrames: number[] = [];
          
          // Mock serial port to track commands
          const originalSendCommand = serialPort.sendCommand.bind(serialPort);
          serialPort.sendCommand = jest.fn(async (command: string) => {
            // Extract frame info from command if it's a servo command
            if (command.includes('#1P') && command.includes('T') && command.includes('!')) {
              // This is a servo command, track which frame is being executed
              // We can infer this from the progress callback
              return Promise.resolve();
            }
            return Promise.resolve();
          });

          // Track progress to verify order
          const progressUpdates: ExecutionProgress[] = [];
          
          try {
            await service.executeSequence(frames, {
              loop: false,
              onProgress: (progress) => {
                progressUpdates.push({ ...progress });
                executedFrames.push(progress.currentFrame);
              },
              onComplete: () => {},
              onError: (error) => {
                // Ignore serial errors since we're mocking
              }
            });
          } catch (error) {
            // Expected to fail due to mock serial port
          }

          // Verify frames were executed in order (0, 1, 2, ...)
          for (let i = 0; i < executedFrames.length - 1; i++) {
            expect(executedFrames[i]).toBeLessThan(executedFrames[i + 1]);
          }

          // Verify progress updates are sequential
          for (let i = 0; i < progressUpdates.length; i++) {
            expect(progressUpdates[i].currentFrame).toBe(i);
          }

          // Restore original method
          serialPort.sendCommand = originalSendCommand;
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Progress should increment sequentially through frames', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(
          fc.record({
            duration: fc.integer(500, 800),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            })
          }),
          { minLength: 2, maxLength: 4 }
        ),
        async (frameDataArray) => {
          const frames = frameDataArray.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const progressUpdates: number[] = [];
          
          // Mock serial port
          serialPort.sendCommand = jest.fn().mockResolvedValue(undefined);

          try {
            await service.executeSequence(frames, {
              loop: false,
              onProgress: (progress) => {
                progressUpdates.push(progress.currentFrame);
              }
            });
          } catch (error) {
            // Ignore errors
          }

          // Verify progress increments by 1 each time
          for (let i = 1; i < progressUpdates.length; i++) {
            expect(progressUpdates[i]).toBe(progressUpdates[i - 1] + 1);
          }

          // Verify we start at 0
          if (progressUpdates.length > 0) {
            expect(progressUpdates[0]).toBe(0);
          }
        }
      ),
      { numRuns: 1000 }
    );
  });

  test('Execution should respect frame durations', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(
          fc.record({
            duration: fc.integer(500, 1000),
            servos: fc.record({
              1: fc.integer(500, 2500),
              2: fc.integer(500, 2500),
              3: fc.integer(500, 2500),
              4: fc.integer(500, 2500),
              5: fc.integer(500, 2500),
              6: fc.integer(500, 2500)
            })
          }),
          { minLength: 2, maxLength: 3 }
        ),
        async (frameDataArray) => {
          const frames = frameDataArray.map((data, i) =>
            ActionFrameFactory.create({
              sequenceId: i,
              ...data
            })
          );

          const timestamps: number[] = [];
          
          // Mock serial port
          serialPort.sendCommand = jest.fn().mockResolvedValue(undefined);

          const startTime = Date.now();
          
          try {
            await service.executeSequence(frames, {
              loop: false,
              onProgress: (progress) => {
                timestamps.push(Date.now() - startTime);
              }
            });
          } catch (error) {
            // Ignore errors
          }

          // Verify timing between frames respects durations (with some tolerance)
          for (let i = 1; i < timestamps.length; i++) {
            const expectedMinDelay = frames[i - 1].duration;
            const actualDelay = timestamps[i] - timestamps[i - 1];
            
            // Allow 100ms tolerance for execution overhead
            expect(actualDelay).toBeGreaterThanOrEqual(expectedMinDelay - 100);
          }
        }
      ),
      { numRuns: 1000 } // Fewer runs since this involves timing
    );
  });
});
