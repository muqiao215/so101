import fc from 'fast-check';
import { CommandBuilder } from '../main/command-builder';
import { ActionFrame } from '../shared/types';

describe('Property Tests - Serialization Round-Trip', () => {
  
  // Feature: robotic-arm-sequencer, Property 12: Serialization Round-Trip
  test('Property 12: Serializing then deserializing frames should produce equivalent frames', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.array(
        fc.record({
          sequenceId: fc.integer({ min: 0, max: 999 }),
          duration: fc.integer({ min: 500, max: 5000 }),
          servos: fc.record({
            1: fc.integer({ min: 500, max: 2500 }),
            2: fc.integer({ min: 500, max: 2500 }),
            3: fc.integer({ min: 500, max: 2500 }),
            4: fc.integer({ min: 500, max: 2500 }),
            5: fc.integer({ min: 500, max: 2500 }),
            6: fc.integer({ min: 500, max: 2500 })
          }),
          soundId: fc.option(fc.integer({ min: 1, max: 255 }), { nil: undefined })
        }),
        { minLength: 1, maxLength: 50 } // Reasonable frame count for testing
      ),
      fc.integer({ min: 1, max: 10 }), // slot ID
      (frameData, slotId) => {
        // Convert generated data to ActionFrame objects
        const originalFrames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          // Test the round-trip through download command
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, originalFrames);
          
          // Parse the download command to extract the serialized data
          const parts = downloadCommand.split(':');
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          // Deserialize the data
          const deserializedFrames = commandBuilder.deserializeFrames(serializedData);
          
          // Check that we got the same number of frames
          if (originalFrames.length !== deserializedFrames.length) {
            return false;
          }
          
          // Check each frame for equivalence
          for (let i = 0; i < originalFrames.length; i++) {
            const original = originalFrames[i];
            const deserialized = deserializedFrames[i];
            
            // Check sequenceId
            if (original.sequenceId !== deserialized.sequenceId) {
              return false;
            }
            
            // Check duration
            if (original.duration !== deserialized.duration) {
              return false;
            }
            
            // Check all servo positions
            for (let servoIndex = 1; servoIndex <= 6; servoIndex++) {
              if (original.servos[servoIndex] !== deserialized.servos[servoIndex]) {
                return false;
              }
            }
            
            // Check soundId (handle undefined case)
            if (original.soundId !== deserialized.soundId) {
              return false;
            }
          }
          
          return true;
        } catch (error) {
          // If serialization/deserialization throws an error, the test fails
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 12: Empty frame list should serialize and deserialize correctly', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 10 }), // slot ID
      (slotId) => {
        const emptyFrames: ActionFrame[] = [];
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, emptyFrames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          const deserialized = commandBuilder.deserializeFrames(serializedData);
          return deserialized.length === 0;
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 12: Single frame should serialize and deserialize correctly', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.record({
        sequenceId: fc.integer({ min: 0, max: 999 }),
        duration: fc.integer({ min: 500, max: 5000 }),
        servos: fc.record({
          1: fc.integer({ min: 500, max: 2500 }),
          2: fc.integer({ min: 500, max: 2500 }),
          3: fc.integer({ min: 500, max: 2500 }),
          4: fc.integer({ min: 500, max: 2500 }),
          5: fc.integer({ min: 500, max: 2500 }),
          6: fc.integer({ min: 500, max: 2500 })
        }),
        soundId: fc.option(fc.integer({ min: 1, max: 255 }), { nil: undefined })
      }),
      fc.integer({ min: 1, max: 10 }), // slot ID
      (frameData, slotId) => {
        const originalFrame: ActionFrame = {
          sequenceId: frameData.sequenceId,
          duration: frameData.duration,
          servos: frameData.servos,
          soundId: frameData.soundId
        };
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, [originalFrame]);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          const deserializedFrames = commandBuilder.deserializeFrames(serializedData);
          
          if (deserializedFrames.length !== 1) {
            return false;
          }
          
          const deserialized = deserializedFrames[0];
          
          return (
            originalFrame.sequenceId === deserialized.sequenceId &&
            originalFrame.duration === deserialized.duration &&
            originalFrame.servos[1] === deserialized.servos[1] &&
            originalFrame.servos[2] === deserialized.servos[2] &&
            originalFrame.servos[3] === deserialized.servos[3] &&
            originalFrame.servos[4] === deserialized.servos[4] &&
            originalFrame.servos[5] === deserialized.servos[5] &&
            originalFrame.servos[6] === deserialized.servos[6] &&
            originalFrame.soundId === deserialized.soundId
          );
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 12: Frames with no sound ID should handle undefined correctly', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.array(
        fc.record({
          sequenceId: fc.integer({ min: 0, max: 999 }),
          duration: fc.integer({ min: 500, max: 5000 }),
          servos: fc.record({
            1: fc.integer({ min: 500, max: 2500 }),
            2: fc.integer({ min: 500, max: 2500 }),
            3: fc.integer({ min: 500, max: 2500 }),
            4: fc.integer({ min: 500, max: 2500 }),
            5: fc.integer({ min: 500, max: 2500 }),
            6: fc.integer({ min: 500, max: 2500 })
          })
          // Intentionally no soundId - should be undefined
        }),
        { minLength: 1, maxLength: 20 }
      ),
      fc.integer({ min: 1, max: 10 }), // slot ID
      (frameData, slotId) => {
        const originalFrames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos
          // soundId is undefined
        }));
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, originalFrames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          const deserializedFrames = commandBuilder.deserializeFrames(serializedData);
          
          if (originalFrames.length !== deserializedFrames.length) {
            return false;
          }
          
          // All deserialized frames should have soundId as undefined
          return deserializedFrames.every(frame => frame.soundId === undefined);
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 12: Frames with maximum values should serialize correctly', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.array(
        fc.record({
          sequenceId: fc.constant(999), // Maximum sequence ID
          duration: fc.constant(5000),  // Maximum duration
          servos: fc.record({
            1: fc.constant(2500), // Maximum PWM
            2: fc.constant(2500),
            3: fc.constant(2500),
            4: fc.constant(2500),
            5: fc.constant(2500),
            6: fc.constant(2500)
          }),
          soundId: fc.constant(255) // Maximum sound ID
        }),
        { minLength: 1, maxLength: 10 }
      ),
      fc.integer({ min: 1, max: 10 }), // slot ID
      (frameData, slotId) => {
        const originalFrames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, originalFrames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          const deserializedFrames = commandBuilder.deserializeFrames(serializedData);
          
          if (originalFrames.length !== deserializedFrames.length) {
            return false;
          }
          
          // Check that maximum values are preserved
          return deserializedFrames.every(frame => 
            frame.sequenceId === 999 &&
            frame.duration === 5000 &&
            Object.values(frame.servos).every(pwm => pwm === 2500) &&
            frame.soundId === 255
          );
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 12: Frames with minimum values should serialize correctly', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.array(
        fc.record({
          sequenceId: fc.constant(0),   // Minimum sequence ID
          duration: fc.constant(500),   // Minimum duration
          servos: fc.record({
            1: fc.constant(500), // Minimum PWM
            2: fc.constant(500),
            3: fc.constant(500),
            4: fc.constant(500),
            5: fc.constant(500),
            6: fc.constant(500)
          }),
          soundId: fc.constant(1) // Minimum sound ID
        }),
        { minLength: 1, maxLength: 10 }
      ),
      fc.integer({ min: 1, max: 10 }), // slot ID
      (frameData, slotId) => {
        const originalFrames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(slotId, originalFrames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          const checksum = parts[checksumIndex];
          
          // Validate checksum
          if (!commandBuilder.validateChecksum(serializedData, checksum)) {
            return false;
          }
          
          const deserializedFrames = commandBuilder.deserializeFrames(serializedData);
          
          if (originalFrames.length !== deserializedFrames.length) {
            return false;
          }
          
          // Check that minimum values are preserved
          return deserializedFrames.every(frame => 
            frame.sequenceId === 0 &&
            frame.duration === 500 &&
            Object.values(frame.servos).every(pwm => pwm === 500) &&
            frame.soundId === 1
          );
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });
});