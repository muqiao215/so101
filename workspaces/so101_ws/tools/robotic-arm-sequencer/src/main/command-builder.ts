import { ActionFrame, ActionProject, Mp3Command } from '../shared/types';

/**
 * CommandBuilder class for generating protocol commands for Arduino communication
 * Handles servo commands, MP3 commands, and batch download operations
 */
export class CommandBuilder {
  
  /**
   * Build servo command for a single ActionFrame
   * Format: #1P<pwm>#2P<pwm>#3P<pwm>#4P<pwm>#5P<pwm>#6P<pwm>T<duration>!
   */
  buildServoCommand(frame: ActionFrame): string {
    const servoCommands = Object.entries(frame.servos)
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([index, pwm]) => `#${index}P${pwm}`)
      .join('');
    return `${servoCommands}T${frame.duration}!`;
  }
  
  /**
   * Build MP3 command for audio control
   */
  buildMp3Command(command: Mp3Command): string {
    switch (command.type) {
      case 'play': 
        return `MP3_PLAY:${command.trackId.toString().padStart(3, '0')}`;
      case 'stop': 
        return 'MP3_STOP';
      case 'next': 
        return 'MP3_NEXT';
      case 'previous': 
        return 'MP3_PREV';
      case 'volume': 
        return `MP3_VOL:${command.level}`;
      default:
        throw new Error(`Unknown MP3 command type: ${(command as any).type}`);
    }
  }
  
  /**
   * Build download command for batch transfer to Arduino
   * Format: CMD_DOWNLOAD:<slot_id>:<frame_count>:<data>:<checksum>
   */
  buildDownloadCommand(slotId: number, frames: ActionFrame[]): string {
    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }
    
    const serialized = this.serializeFrames(frames);
    const checksum = this.calculateChecksum(serialized);
    return `CMD_DOWNLOAD:${slotId}:${frames.length}:${serialized}:${checksum}`;
  }
  
  /**
   * Build format command to clear Arduino storage
   * Format: CMD_FORMAT:<slot_id>
   */
  buildFormatCommand(slotId: number): string {
    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }
    return `CMD_FORMAT:${slotId}`;
  }
  
  /**
   * Build set offline command to enable autonomous execution
   * Format: CMD_SET_OFFLINE:<slot_id>
   */
  buildSetOfflineCommand(slotId: number): string {
    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }
    return `CMD_SET_OFFLINE:${slotId}`;
  }
  
  /**
   * Build read command to verify stored sequence
   * Format: CMD_READ:<slot_id>
   */
  buildReadCommand(slotId: number): string {
    if (slotId < 1 || slotId > 10) {
      throw new Error(`Invalid slot ID: ${slotId}. Must be between 1-10`);
    }
    return `CMD_READ:${slotId}`;
  }
  
  /**
   * Serialize frames into binary format for Arduino EEPROM
   * Each frame is 17 bytes: [sequenceId:2][duration:2][servo1:2][servo2:2][servo3:2][servo4:2][servo5:2][servo6:2][soundId:1]
   */
  private serializeFrames(frames: ActionFrame[]): string {
    return frames.map(frame => {
      const parts = [
        frame.sequenceId.toString(16).padStart(4, '0'),
        frame.duration.toString(16).padStart(4, '0'),
        ...Object.values(frame.servos).map(pwm => pwm.toString(16).padStart(4, '0')),
        (frame.soundId || 0).toString(16).padStart(2, '0')
      ];
      return parts.join('');
    }).join('|'); // Use pipe separator instead of colon to avoid conflicts
  }
  
  /**
   * Calculate checksum for data integrity verification
   */
  private calculateChecksum(data: string): string {
    return data.split('').reduce((acc, char) => (acc + char.charCodeAt(0)) % 256, 0)
      .toString(16).padStart(2, '0');
  }
  
  /**
   * Deserialize frames from Arduino response for verification
   */
  deserializeFrames(serializedData: string): ActionFrame[] {
    if (serializedData === '') {
      return [];
    }
    
    const frameStrings = serializedData.split('|'); // Use pipe separator
    return frameStrings.map(frameStr => {
      if (frameStr.length !== 34) { // 17 bytes * 2 hex chars per byte = 34 chars
        throw new Error(`Invalid frame data length: ${frameStr.length}, expected 34`);
      }
      
      const sequenceId = parseInt(frameStr.substring(0, 4), 16);
      const duration = parseInt(frameStr.substring(4, 8), 16);
      const servos: Record<number, number> = {};
      
      for (let i = 0; i < 6; i++) {
        const startPos = 8 + (i * 4);
        servos[i + 1] = parseInt(frameStr.substring(startPos, startPos + 4), 16);
      }
      
      const soundId = parseInt(frameStr.substring(32, 34), 16);
      
      return {
        sequenceId,
        duration,
        servos,
        soundId: soundId === 0 ? undefined : soundId
      };
    });
  }
  
  /**
   * Validate checksum of received data
   */
  validateChecksum(data: string, receivedChecksum: string): boolean {
    const calculatedChecksum = this.calculateChecksum(data);
    return calculatedChecksum === receivedChecksum.toLowerCase();
  }
  
  /**
   * Split large data into chunks for transmission (max 256 bytes per chunk)
   */
  chunkData(data: string, maxChunkSize: number = 256): string[] {
    const chunks: string[] = [];
    for (let i = 0; i < data.length; i += maxChunkSize) {
      chunks.push(data.substring(i, i + maxChunkSize));
    }
    return chunks;
  }
}