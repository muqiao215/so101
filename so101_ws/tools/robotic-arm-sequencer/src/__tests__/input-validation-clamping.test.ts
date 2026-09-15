import fc from 'fast-check';
import { ActionFrameFactory } from '../shared/factories';
import { ValidationService } from '../shared/validation';

describe('Property Tests - Input Validation and Clamping', () => {
  
  // Feature: robotic-arm-sequencer, Property 1: Input Validation and Clamping
  test('Property 1: PWM values should be clamped to 500-2500 range', () => {
    fc.assert(fc.property(
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer({ min: 500, max: 5000 }),
      fc.integer({ min: 0, max: 100 }),
      (pwm1, pwm2, pwm3, pwm4, pwm5, pwm6, duration, sequenceId) => {
        // Create frame with potentially out-of-range PWM values
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration,
          servos: {
            1: pwm1,
            2: pwm2,
            3: pwm3,
            4: pwm4,
            5: pwm5,
            6: pwm6
          }
        });
        
        // All PWM values should be clamped to 500-2500 range
        const allPWMsInRange = Object.values(frame.servos).every(pwm => 
          pwm >= 500 && pwm <= 2500
        );
        
        return allPWMsInRange;
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: Duration values should be clamped to 500-5000ms range', () => {
    fc.assert(fc.property(
      fc.integer(),
      fc.integer({ min: 0, max: 100 }),
      (duration, sequenceId) => {
        // Create frame with potentially out-of-range duration
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration,
          servos: {
            1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500
          }
        });
        
        // Duration should be clamped to 500-5000ms range
        return frame.duration >= 500 && frame.duration <= 5000;
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: Sound ID values should be clamped to 1-255 range', () => {
    fc.assert(fc.property(
      fc.integer(),
      fc.integer({ min: 0, max: 100 }),
      (soundId, sequenceId) => {
        // Create frame with potentially out-of-range sound ID
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration: 1000,
          servos: {
            1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500
          },
          soundId
        });
        
        // Sound ID should be clamped to 1-255 range or undefined
        return frame.soundId === undefined || 
               (frame.soundId >= 1 && frame.soundId <= 255);
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: Extreme PWM values should be properly clamped', () => {
    fc.assert(fc.property(
      fc.record({
        extremePWM: fc.oneof(
          fc.integer({ min: -1000000, max: 499 }),  // Below minimum
          fc.integer({ min: 2501, max: 1000000 })   // Above maximum
        ),
        sequenceId: fc.integer({ min: 0, max: 100 })
      }),
      ({ extremePWM, sequenceId }) => {
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration: 1000,
          servos: {
            1: extremePWM,
            2: extremePWM,
            3: extremePWM,
            4: extremePWM,
            5: extremePWM,
            6: extremePWM
          }
        });
        
        // All extreme values should be clamped to valid range
        // Values <= 499 should be clamped to 500
        // Values >= 2501 should be clamped to 2500
        const expectedValue = extremePWM <= 499 ? 500 : 2500;
        const allClamped = Object.values(frame.servos).every(pwm => pwm === expectedValue);
        
        return allClamped;
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: Extreme duration values should be properly clamped', () => {
    fc.assert(fc.property(
      fc.record({
        extremeDuration: fc.oneof(
          fc.integer({ min: -1000000, max: 499 }),  // Below minimum
          fc.integer({ min: 5001, max: 1000000 })   // Above maximum
        ),
        sequenceId: fc.integer({ min: 0, max: 100 })
      }),
      ({ extremeDuration, sequenceId }) => {
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration: extremeDuration,
          servos: {
            1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500
          }
        });
        
        // Duration should be clamped to valid range
        const expectedValue = extremeDuration < 500 ? 500 : 5000;
        return frame.duration === expectedValue;
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: Missing servo values should default to 1500 (center position)', () => {
    fc.assert(fc.property(
      fc.integer({ min: 0, max: 100 }),
      fc.record({
        1: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined }),
        2: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined }),
        3: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined }),
        4: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined }),
        5: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined }),
        6: fc.option(fc.integer({ min: 500, max: 2500 }), { nil: undefined })
      }),
      (sequenceId, partialServos) => {
        // Create servos object with some potentially missing values
        const servos: Record<number, number> = {};
        for (let i = 1; i <= 6; i++) {
          if (partialServos[i as keyof typeof partialServos] !== undefined) {
            servos[i] = partialServos[i as keyof typeof partialServos]!;
          }
          // Some servos intentionally missing
        }
        
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration: 1000,
          servos
        });
        
        // All 6 servos should be present, missing ones defaulted to 1500
        const hasAllServos = Object.keys(frame.servos).length === 6;
        const allInRange = Object.values(frame.servos).every(pwm => 
          pwm >= 500 && pwm <= 2500
        );
        
        // Check that missing servos got default value of 1500
        let defaultsCorrect = true;
        for (let i = 1; i <= 6; i++) {
          if (partialServos[i as keyof typeof partialServos] === undefined) {
            if (frame.servos[i] !== 1500) {
              defaultsCorrect = false;
            }
          }
        }
        
        return hasAllServos && allInRange && defaultsCorrect;
      }
    ), { numRuns: 1000 });
  });

  test('Property 1: ValidationService should correctly identify valid frames after clamping', () => {
    fc.assert(fc.property(
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer(),
      fc.integer({ min: 0, max: 100 }),
      fc.option(fc.integer(), { nil: undefined }),
      (pwm1, pwm2, pwm3, pwm4, pwm5, pwm6, duration, sequenceId, soundId) => {
        // Create frame with potentially invalid values
        const frame = ActionFrameFactory.create({
          sequenceId,
          duration,
          servos: { 1: pwm1, 2: pwm2, 3: pwm3, 4: pwm4, 5: pwm5, 6: pwm6 },
          soundId
        });
        
        // After factory clamping, validation should always pass
        const validation = ValidationService.validateFrame(frame);
        
        return validation.isValid;
      }
    ), { numRuns: 1000 });
  });
});