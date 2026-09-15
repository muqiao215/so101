import { ActionFrame, ActionProject, ValidationResult } from './types';
import { randomUUID } from 'crypto';

export class ActionFrameFactory {
  static create(data: {
    sequenceId: number;
    duration: number;
    servos: Record<number, number>;
    soundId?: number;
  }): ActionFrame {
    // Clamp duration to valid range
    const clampedDuration = Math.max(500, Math.min(5000, data.duration));
    
    // Clamp servo values to valid range
    const clampedServos: Record<number, number> = {};
    for (let i = 1; i <= 6; i++) {
      const pwm = data.servos[i] !== undefined ? data.servos[i] : 1500;
      clampedServos[i] = Math.max(500, Math.min(2500, pwm));
    }
    
    // Clamp sound ID to valid range
    const clampedSoundId = data.soundId ? 
      Math.max(1, Math.min(255, data.soundId)) : undefined;
    
    return {
      sequenceId: data.sequenceId,
      duration: clampedDuration,
      servos: clampedServos,
      soundId: clampedSoundId
    };
  }
  
  static validate(frame: ActionFrame): ValidationResult {
    const errors: string[] = [];
    
    if (frame.duration < 500 || frame.duration > 5000) {
      errors.push(`Duration must be between 500-5000ms, got ${frame.duration}`);
    }
    
    Object.entries(frame.servos).forEach(([index, pwm]) => {
      if (pwm < 500 || pwm > 2500) {
        errors.push(`Servo ${index} PWM must be between 500-2500, got ${pwm}`);
      }
    });
    
    if (frame.soundId && (frame.soundId < 1 || frame.soundId > 255)) {
      errors.push(`Sound ID must be between 1-255, got ${frame.soundId}`);
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
}

export class ActionProjectFactory {
  static create(data: {
    name: string;
    frames?: ActionFrame[];
    remoteSlotId?: number;
  }): ActionProject {
    // Truncate name to 50 characters
    const truncatedName = data.name.substring(0, 50);
    
    // Validate remote slot ID
    const validSlotId = data.remoteSlotId && 
      data.remoteSlotId >= 1 && data.remoteSlotId <= 10 ? 
      data.remoteSlotId : undefined;
    
    return {
      id: randomUUID(),
      name: truncatedName,
      frames: data.frames || [],
      remoteSlotId: validSlotId,
      createdAt: Date.now(),
      modifiedAt: Date.now()
    };
  }
  
  static validate(project: ActionProject): ValidationResult {
    const errors: string[] = [];
    
    if (!project.id || project.id.length === 0) {
      errors.push('Project ID is required');
    }
    
    if (!project.name || project.name.length === 0) {
      errors.push('Project name is required');
    }
    
    if (project.name && project.name.length > 50) {
      errors.push(`Project name must be 50 characters or less, got ${project.name.length}`);
    }
    
    if (project.remoteSlotId && (project.remoteSlotId < 1 || project.remoteSlotId > 10)) {
      errors.push(`Remote slot ID must be between 1-10, got ${project.remoteSlotId}`);
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
}