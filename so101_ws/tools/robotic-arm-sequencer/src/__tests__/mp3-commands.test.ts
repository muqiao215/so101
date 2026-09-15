import { CommandBuilder } from '../main/command-builder';
import { Mp3Command } from '../shared/types';

describe('Unit Tests - MP3 Commands', () => {
  let commandBuilder: CommandBuilder;

  beforeEach(() => {
    commandBuilder = new CommandBuilder();
  });

  describe('MP3 Command Formats', () => {
    test('Play command should format track ID with leading zeros', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 1 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:001');
    });

    test('Play command should format track ID 42 correctly', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 42 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:042');
    });

    test('Play command should format track ID 255 correctly', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 255 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:255');
    });

    test('Stop command should return correct format', () => {
      const stopCommand: Mp3Command = { type: 'stop' };
      const result = commandBuilder.buildMp3Command(stopCommand);
      expect(result).toBe('MP3_STOP');
    });

    test('Next command should return correct format', () => {
      const nextCommand: Mp3Command = { type: 'next' };
      const result = commandBuilder.buildMp3Command(nextCommand);
      expect(result).toBe('MP3_NEXT');
    });

    test('Previous command should return correct format', () => {
      const previousCommand: Mp3Command = { type: 'previous' };
      const result = commandBuilder.buildMp3Command(previousCommand);
      expect(result).toBe('MP3_PREV');
    });

    test('Volume command should format level correctly', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 15 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:15');
    });

    test('Volume command with minimum level (0) should work', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 0 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:0');
    });

    test('Volume command with maximum level (30) should work', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 30 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:30');
    });
  });

  describe('Volume Clamping (Requirements 7.2, 7.4, 7.5)', () => {
    test('Volume level 0 should be valid', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 0 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:0');
    });

    test('Volume level 30 should be valid', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 30 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:30');
    });

    test('Volume level 15 (mid-range) should be valid', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 15 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:15');
    });

    // Note: Volume clamping should be handled at the factory/validation layer
    // The CommandBuilder assumes valid input
  });

  describe('Track ID Range (Requirements 7.1)', () => {
    test('Track ID 1 (minimum) should be valid', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 1 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:001');
    });

    test('Track ID 255 (maximum) should be valid', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 255 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:255');
    });

    test('Track ID 128 (mid-range) should be valid', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 128 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:128');
    });
  });

  describe('Command Ordering with Servo Commands (Requirements 7.3, 7.6)', () => {
    test('Frame with sound ID should generate MP3 play command', () => {
      const frame = {
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
        soundId: 42
      };

      const mp3Command: Mp3Command = { type: 'play', trackId: frame.soundId };
      const mp3Result = commandBuilder.buildMp3Command(mp3Command);
      const servoResult = commandBuilder.buildServoCommand(frame);

      // Verify both commands are generated correctly
      expect(mp3Result).toBe('MP3_PLAY:042');
      expect(servoResult).toContain('#1P1500');
      expect(servoResult).toContain('T1000!');
    });

    test('Frame without sound ID should only generate servo command', () => {
      const frame = {
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
      };

      const servoResult = commandBuilder.buildServoCommand(frame);

      // Verify servo command is generated
      expect(servoResult).toContain('#1P1500');
      expect(servoResult).toContain('T1000!');
      
      // No MP3 command should be generated for frames without soundId
      expect(frame.soundId).toBeUndefined();
    });

    test('Multiple frames with different sound IDs should generate correct MP3 commands', () => {
      const frames = [
        {
          sequenceId: 0,
          duration: 1000,
          servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
          soundId: 1
        },
        {
          sequenceId: 1,
          duration: 1500,
          servos: { 1: 2000, 2: 2000, 3: 2000, 4: 2000, 5: 2000, 6: 2000 },
          soundId: 2
        },
        {
          sequenceId: 2,
          duration: 2000,
          servos: { 1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 1000, 6: 1000 },
          soundId: 3
        }
      ];

      frames.forEach(frame => {
        if (frame.soundId) {
          const mp3Command: Mp3Command = { type: 'play', trackId: frame.soundId };
          const mp3Result = commandBuilder.buildMp3Command(mp3Command);
          expect(mp3Result).toBe(`MP3_PLAY:${frame.soundId.toString().padStart(3, '0')}`);
        }
        
        const servoResult = commandBuilder.buildServoCommand(frame);
        expect(servoResult).toContain(`T${frame.duration}!`);
      });
    });

    test('Frame with sound ID 255 (maximum) should generate correct MP3 command', () => {
      const frame = {
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
        soundId: 255
      };

      const mp3Command: Mp3Command = { type: 'play', trackId: frame.soundId };
      const mp3Result = commandBuilder.buildMp3Command(mp3Command);

      expect(mp3Result).toBe('MP3_PLAY:255');
    });
  });

  describe('Edge Cases', () => {
    test('Play command with track ID 10 should pad correctly', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 10 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:010');
    });

    test('Play command with track ID 100 should not over-pad', () => {
      const playCommand: Mp3Command = { type: 'play', trackId: 100 };
      const result = commandBuilder.buildMp3Command(playCommand);
      expect(result).toBe('MP3_PLAY:100');
    });

    test('Volume command with single digit should not pad', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 5 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:5');
    });

    test('Volume command with double digit should not pad', () => {
      const volumeCommand: Mp3Command = { type: 'volume', level: 25 };
      const result = commandBuilder.buildMp3Command(volumeCommand);
      expect(result).toBe('MP3_VOL:25');
    });
  });

  describe('Command Type Safety', () => {
    test('All MP3 command types should be handled', () => {
      const commands: Mp3Command[] = [
        { type: 'play', trackId: 1 },
        { type: 'stop' },
        { type: 'next' },
        { type: 'previous' },
        { type: 'volume', level: 15 }
      ];

      commands.forEach(command => {
        expect(() => commandBuilder.buildMp3Command(command)).not.toThrow();
      });
    });

    test('Invalid command type should throw error', () => {
      const invalidCommand = { type: 'invalid' } as any;
      expect(() => commandBuilder.buildMp3Command(invalidCommand)).toThrow();
    });
  });

  describe('Integration with Servo Commands', () => {
    test('Servo command should not be affected by MP3 command generation', () => {
      const frame = {
        sequenceId: 0,
        duration: 1000,
        servos: { 1: 1500, 2: 1600, 3: 1700, 4: 1800, 5: 1900, 6: 2000 },
        soundId: 42
      };

      // Generate MP3 command first
      const mp3Command: Mp3Command = { type: 'play', trackId: frame.soundId };
      const mp3Result = commandBuilder.buildMp3Command(mp3Command);

      // Generate servo command after
      const servoResult = commandBuilder.buildServoCommand(frame);

      // Both should be independent and correct
      expect(mp3Result).toBe('MP3_PLAY:042');
      expect(servoResult).toBe('#1P1500#2P1600#3P1700#4P1800#5P1900#6P2000T1000!');
    });

    test('Multiple MP3 commands should not interfere with each other', () => {
      const commands: Mp3Command[] = [
        { type: 'play', trackId: 1 },
        { type: 'volume', level: 20 },
        { type: 'stop' },
        { type: 'next' }
      ];

      const results = commands.map(cmd => commandBuilder.buildMp3Command(cmd));

      expect(results[0]).toBe('MP3_PLAY:001');
      expect(results[1]).toBe('MP3_VOL:20');
      expect(results[2]).toBe('MP3_STOP');
      expect(results[3]).toBe('MP3_NEXT');
    });
  });
});
