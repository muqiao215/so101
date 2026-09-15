import fc from 'fast-check';
import { CommandBuilder } from '../main/command-builder';
import { ActionFrame } from '../shared/types';

describe('Property Tests - Download Chunking Correctness', () => {
  
  // Feature: robotic-arm-sequencer, Property 13: Download Chunking Correctness
  test('Property 13: Data should be split into chunks where each chunk is ≤ 256 bytes', () => {
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
        { minLength: 1, maxLength: 100 } // Test with larger frame counts to ensure chunking
      ),
      fc.integer({ min: 1, max: 256 }), // Variable chunk size
      (frameData, maxChunkSize) => {
        const frames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          // Build download command to get serialized data
          const downloadCommand = commandBuilder.buildDownloadCommand(1, frames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          
          // Chunk the data
          const chunks = commandBuilder.chunkData(serializedData, maxChunkSize);
          
          // Verify each chunk is ≤ maxChunkSize
          const allChunksValid = chunks.every(chunk => chunk.length <= maxChunkSize);
          
          // Verify concatenation of all chunks equals original data
          const reconstructed = chunks.join('');
          const dataMatches = reconstructed === serializedData;
          
          return allChunksValid && dataMatches;
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Chunking with default 256 byte limit should work correctly', () => {
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
        { minLength: 1, maxLength: 100 }
      ),
      (frameData) => {
        const frames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(1, frames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          
          // Use default chunk size (256)
          const chunks = commandBuilder.chunkData(serializedData);
          
          // Verify each chunk is ≤ 256 bytes
          const allChunksValid = chunks.every(chunk => chunk.length <= 256);
          
          // Verify concatenation equals original
          const reconstructed = chunks.join('');
          const dataMatches = reconstructed === serializedData;
          
          return allChunksValid && dataMatches;
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Empty data should produce empty chunk array', () => {
    const commandBuilder = new CommandBuilder();
    
    const chunks = commandBuilder.chunkData('');
    expect(chunks).toEqual([]);
  });

  test('Property 13: Data smaller than chunk size should produce single chunk', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }),
      fc.integer({ min: 101, max: 500 }),
      (data, chunkSize) => {
        const chunks = commandBuilder.chunkData(data, chunkSize);
        return chunks.length === 1 && chunks[0] === data;
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Data exactly equal to chunk size should produce single chunk', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 500 }),
      (size) => {
        const data = 'x'.repeat(size);
        const chunks = commandBuilder.chunkData(data, size);
        return chunks.length === 1 && chunks[0] === data;
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Large data should be split into multiple chunks', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.integer({ min: 257, max: 1000 }),
      (dataLength) => {
        const data = 'x'.repeat(dataLength);
        const chunks = commandBuilder.chunkData(data, 256);
        
        // Should have more than one chunk
        const hasMultipleChunks = chunks.length > 1;
        
        // All chunks except possibly the last should be exactly 256 bytes
        const allButLastAreMaxSize = chunks.slice(0, -1).every(chunk => chunk.length === 256);
        
        // Last chunk should be ≤ 256 bytes
        const lastChunkValid = chunks[chunks.length - 1].length <= 256;
        
        // Concatenation should equal original
        const reconstructed = chunks.join('');
        const dataMatches = reconstructed === data;
        
        return hasMultipleChunks && allButLastAreMaxSize && lastChunkValid && dataMatches;
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Chunk count should be correct for given data length', () => {
    const commandBuilder = new CommandBuilder();
    
    fc.assert(fc.property(
      fc.integer({ min: 1, max: 2000 }),
      fc.integer({ min: 1, max: 500 }),
      (dataLength, chunkSize) => {
        const data = 'x'.repeat(dataLength);
        const chunks = commandBuilder.chunkData(data, chunkSize);
        
        // Expected chunk count
        const expectedChunkCount = Math.ceil(dataLength / chunkSize);
        
        return chunks.length === expectedChunkCount;
      }
    ), { numRuns: 1000 });
  });

  test('Property 13: Chunking should preserve data integrity for real frame data', () => {
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
        { minLength: 10, maxLength: 100 } // Larger frame counts to ensure chunking happens
      ),
      (frameData) => {
        const frames: ActionFrame[] = frameData.map(data => ({
          sequenceId: data.sequenceId,
          duration: data.duration,
          servos: data.servos,
          soundId: data.soundId
        }));
        
        try {
          const downloadCommand = commandBuilder.buildDownloadCommand(1, frames);
          const parts = downloadCommand.split(':');
          
          const dataStartIndex = 3;
          const checksumIndex = parts.length - 1;
          const dataParts = parts.slice(dataStartIndex, checksumIndex);
          const serializedData = dataParts.join(':');
          
          // Chunk the data
          const chunks = commandBuilder.chunkData(serializedData, 256);
          
          // Reconstruct from chunks
          const reconstructed = chunks.join('');
          
          // Deserialize reconstructed data
          const deserializedFrames = commandBuilder.deserializeFrames(reconstructed);
          
          // Should have same number of frames
          if (frames.length !== deserializedFrames.length) {
            return false;
          }
          
          // All frames should match
          for (let i = 0; i < frames.length; i++) {
            const original = frames[i];
            const deserialized = deserializedFrames[i];
            
            if (original.sequenceId !== deserialized.sequenceId ||
                original.duration !== deserialized.duration ||
                original.soundId !== deserialized.soundId) {
              return false;
            }
            
            for (let servoIndex = 1; servoIndex <= 6; servoIndex++) {
              if (original.servos[servoIndex] !== deserialized.servos[servoIndex]) {
                return false;
              }
            }
          }
          
          return true;
        } catch (error) {
          return false;
        }
      }
    ), { numRuns: 1000 });
  });
});
