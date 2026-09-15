import fc from 'fast-check';
import { CommandBuilder } from '../main/command-builder';
import { ActionFrame } from '../shared/types';

describe('Property Tests - Serial Command Format', () => {
  let commandBuilder: CommandBuilder;

  beforeEach(() => {
    commandBuilder = new CommandBuilder();
  });

  // Feature: robotic-arm-sequencer, Property 8: Serial Command Format Correctness
  test('Property 8: Serial command format should be correct for all valid ActionFrames', () => {
    fc.assert(fc.property(
      fc.integer({ min: 0, max: 999 }), // sequenceId
      fc.integer({ min: 500, max: 5000 }), // duration
      fc.integer({ min: 500, max: 2500 }), // servo1 PWM
      fc.integer({ min: 500, max: 2500 }), // servo2 PWM
      fc.integer({ min: 500, max: 2500 }), // servo3 PWM
      fc.integer({ min: 500, max: 2500 }), // servo4 PWM
      fc.integer({ min: 500, max: 2500 }), // servo5 PWM
      fc.integer({ min: 500, max: 2500 }), // servo6 PWM
      fc.option(fc.integer({ min: 1, max: 255 })), // optional soundId
      (sequenceId, duration, servo1, servo2, servo3, servo4, servo5, servo6, soundId) => {
        const frame: ActionFrame = {
          sequenceId,
          duration,
          servos: {
            1: servo1,
            2: servo2,
            3: servo3,
            4: servo4,
            5: servo5,
            6: servo6
          },
          soundId
        };

        const command = commandBuilder.buildServoCommand(frame);

        // Validate command format: #1P<pwm>#2P<pwm>#3P<pwm>#4P<pwm>#5P<pwm>#6P<pwm>T<duration>!
        
        // Should start with #1P
        expect(command).toMatch(/^#1P/);
        
        // Should contain exactly 6 servo commands in order
        expect(command).toMatch(/^#1P\d+#2P\d+#3P\d+#4P\d+#5P\d+#6P\d+T\d+!$/);
        
        // Should end with T<duration>!
        expect(command).toMatch(new RegExp(`T${duration}!$`));
        
        // Extract and validate PWM values
        const servoMatches = command.match(/#(\d+)P(\d+)/g);
        expect(servoMatches).toHaveLength(6);
        
        servoMatches?.forEach((match, index) => {
          const [, servoIndex, pwmValue] = match.match(/#(\d+)P(\d+)/)!;
          expect(parseInt(servoIndex)).toBe(index + 1);
          const pwm = parseInt(pwmValue);
          expect(pwm).toBeGreaterThanOrEqual(500);
          expect(pwm).toBeLessThanOrEqual(2500);
          expect(pwm).toBe(frame.servos[index + 1]);
        });
        
        // Validate duration
        const durationMatch = command.match(/T(\d+)!/);
        expect(durationMatch).toBeTruthy();
        const extractedDuration = parseInt(durationMatch![1]);
        expect(extractedDuration).toBe(duration);
        expect(extractedDuration).toBeGreaterThanOrEqual(500);
        expect(extractedDuration).toBeLessThanOrEqual(5000);
      }
    ), { numRuns: 1000 });
  });

  test('Property 8: Serial command should handle edge case PWM values correctly', () => {
    fc.assert(fc.property(
      fc.integer({ min: 0, max: 999 }), // sequenceId
      fc.constantFrom(500, 2500), // edge case durations
      fc.constantFrom(500, 2500), // edge case PWM values
      (sequenceId, duration, pwm) => {
        const frame: ActionFrame = {
          sequenceId,
          duration,
          servos: {
            1: pwm,
            2: pwm,
            3: pwm,
            4: pwm,
            5: pwm,
            6: pwm
          }
        };

        const command = commandBuilder.buildServoCommand(frame);
        
        // Should contain the exact PWM values
        expect(command).toContain(`#1P${pwm}`);
        expect(command).toContain(`#2P${pwm}`);
        expect(command).toContain(`#3P${pwm}`);
        expect(command).toContain(`#4P${pwm}`);
        expect(command).toContain(`#5P${pwm}`);
        expect(command).toContain(`#6P${pwm}`);
        expect(command).toContain(`T${duration}!`);
      }
    ), { numRuns: 1000 });
  });

  test('Property 8: Serial command format should be consistent regardless of servo order in input', () => {
    fc.assert(fc.property(
      fc.integer({ min: 0, max: 999 }), // sequenceId
      fc.integer({ min: 500, max: 5000 }), // duration
      fc.integer({ min: 500, max: 2500 }), // servo1 PWM
      fc.integer({ min: 500, max: 2500 }), // servo2 PWM
      fc.integer({ min: 500, max: 2500 }), // servo3 PWM
      fc.integer({ min: 500, max: 2500 }), // servo4 PWM
      fc.integer({ min: 500, max: 2500 }), // servo5 PWM
      fc.integer({ min: 500, max: 2500 }), // servo6 PWM
      (sequenceId, duration, servo1, servo2, servo3, servo4, servo5, servo6) => {
        // Create frame with servos in different order
        const frameUnordered: ActionFrame = {
          sequenceId,
          duration,
          servos: {
            6: servo6,
            1: servo1,
            4: servo4,
            2: servo2,
            5: servo5,
            3: servo3
          }
        };

        const frameOrdered: ActionFrame = {
          sequenceId,
          duration,
          servos: {
            1: servo1,
            2: servo2,
            3: servo3,
            4: servo4,
            5: servo5,
            6: servo6
          }
        };

        const commandUnordered = commandBuilder.buildServoCommand(frameUnordered);
        const commandOrdered = commandBuilder.buildServoCommand(frameOrdered);
        
        // Commands should be identical regardless of input order
        expect(commandUnordered).toBe(commandOrdered);
        
        // Should always be in order #1P...#2P...#3P...#4P...#5P...#6P...
        expect(commandUnordered).toMatch(/^#1P\d+#2P\d+#3P\d+#4P\d+#5P\d+#6P\d+T\d+!$/);
      }
    ), { numRuns: 1000 });
  });
});