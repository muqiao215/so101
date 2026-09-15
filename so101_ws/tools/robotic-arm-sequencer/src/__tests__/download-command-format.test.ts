import fc from 'fast-check';
import { CommandBuilder } from '../main/command-builder';
import { ActionFrame } from '../shared/types';

describe('Property Tests - Download Command Format', () => {
  let commandBuilder: CommandBuilder;

  beforeEach(() => {
    commandBuilder = new CommandBuilder();
  });

  // Feature: robotic-arm-sequencer, Property 15: Download Command Format
  test('Property 15: Download command format should match CMD_DOWNLOAD:<slot_id>:<frame_count>:<data>:<checksum>', () => {
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 10 }), // slotId
      fc.array(fc.record({
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
        soundId: fc.option(fc.integer({ min: 1, max: 255 }))
      }), { minLength: 1, maxLength: 20 }),
      (slotId, frames) => {
        const command = commandBuilder.buildDownloadCommand(slotId, frames);
        
        // Should start with CMD_DOWNLOAD:
        expect(command).toMatch(/^CMD_DOWNLOAD:/);
        
        // Split into parts - be careful with the data part that may contain separators
        const parts = command.split(':');
        
        // Should have at least 5 parts: CMD_DOWNLOAD, slot_id, frame_count, data, checksum
        expect(parts.length).toBeGreaterThanOrEqual(5);
        
        // Validate each part
        expect(parts[0]).toBe('CMD_DOWNLOAD');
        
        // Slot ID should match input and be in valid range
        const extractedSlotId = parseInt(parts[1]);
        expect(extractedSlotId).toBe(slotId);
        expect(extractedSlotId).toBeGreaterThanOrEqual(1);
        expect(extractedSlotId).toBeLessThanOrEqual(10);
        
        // Frame count should match actual frame count
        const extractedFrameCount = parseInt(parts[2]);
        expect(extractedFrameCount).toBe(frames.length);
        expect(extractedFrameCount).toBeGreaterThan(0);
        
        // Data part should be non-empty (parts[3] to parts[parts.length-2] joined)
        const dataStartIndex = 3;
        const checksumIndex = parts.length - 1;
        const dataParts = parts.slice(dataStartIndex, checksumIndex);
        const data = dataParts.join(':');
        expect(data).toBeTruthy();
        expect(data.length).toBeGreaterThan(0);
        
        // Checksum part should be non-empty
        const checksum = parts[checksumIndex];
        expect(checksum).toBeTruthy();
        expect(checksum.length).toBeGreaterThan(0);
      }
    ), { numRuns: 1000 });
  });

  test('Property 15: Download command should handle edge case slot IDs correctly', () => {
    fc.assert(fc.property(
      fc.constantFrom(1, 10), // edge case slot IDs
      fc.array(fc.record({
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
        soundId: fc.option(fc.integer({ min: 1, max: 255 }))
      }), { minLength: 1, maxLength: 5 }),
      (slotId, frames) => {
        const command = commandBuilder.buildDownloadCommand(slotId, frames);
        const parts = command.split(':');
        
        // Should correctly handle edge case slot IDs
        expect(parts[1]).toBe(slotId.toString());
        expect(parseInt(parts[1])).toBe(slotId);
      }
    ), { numRuns: 1000 });
  });

  test('Property 15: Download command should reject invalid slot IDs', () => {
    fc.assert(fc.property(
      fc.integer().filter(n => n < 1 || n > 10), // invalid slot IDs
      fc.array(fc.record({
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
        soundId: fc.option(fc.integer({ min: 1, max: 255 }))
      }), { minLength: 1, maxLength: 5 }),
      (invalidSlotId, frames) => {
        // Should throw an error for invalid slot IDs
        expect(() => {
          commandBuilder.buildDownloadCommand(invalidSlotId, frames);
        }).toThrow(/Invalid slot ID/);
      }
    ), { numRuns: 1000 });
  });

  test('Property 15: Download command should handle empty and single frame arrays', () => {
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 10 }), // slotId
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
        soundId: fc.option(fc.integer({ min: 1, max: 255 }))
      }),
      (slotId, frame) => {
        // Test single frame
        const singleFrameCommand = commandBuilder.buildDownloadCommand(slotId, [frame]);
        const parts = singleFrameCommand.split(':');
        
        expect(parts[0]).toBe('CMD_DOWNLOAD');
        expect(parts[1]).toBe(slotId.toString());
        expect(parts[2]).toBe('1'); // frame count should be 1
        expect(parts[3]).toBeTruthy(); // data should exist
        expect(parts[4]).toBeTruthy(); // checksum should exist
      }
    ), { numRuns: 1000 });
  });

  test('Property 15: Download command format should be consistent for identical inputs', () => {
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 10 }), // slotId
      fc.array(fc.record({
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
        soundId: fc.option(fc.integer({ min: 1, max: 255 }))
      }), { minLength: 1, maxLength: 10 }),
      (slotId, frames) => {
        // Generate command twice with same inputs
        const command1 = commandBuilder.buildDownloadCommand(slotId, frames);
        const command2 = commandBuilder.buildDownloadCommand(slotId, frames);
        
        // Commands should be identical
        expect(command1).toBe(command2);
        
        // Both should have correct format
        expect(command1).toMatch(/^CMD_DOWNLOAD:\d+:\d+:.+:.+$/);
        expect(command2).toMatch(/^CMD_DOWNLOAD:\d+:\d+:.+:.+$/);
      }
    ), { numRuns: 1000 });
  });
});