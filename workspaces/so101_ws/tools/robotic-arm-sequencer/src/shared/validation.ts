import { ActionFrame, ActionProject, ValidationResult } from './types';

export class ValidationService {
  /**
   * Validates an ActionFrame with comprehensive error messages
   */
  static validateFrame(frame: ActionFrame): ValidationResult {
    const errors: string[] = [];
    
    // Validate sequenceId
    if (typeof frame.sequenceId !== 'number' || frame.sequenceId < 0) {
      errors.push(`Sequence ID must be a non-negative number, got ${frame.sequenceId}`);
    }
    
    // Validate duration
    if (typeof frame.duration !== 'number') {
      errors.push(`Duration must be a number, got ${typeof frame.duration}`);
    } else if (frame.duration < 500 || frame.duration > 5000) {
      errors.push(`Duration must be between 500-5000ms for safe servo operation, got ${frame.duration}ms`);
    }
    
    // Validate servos object
    if (!frame.servos || typeof frame.servos !== 'object') {
      errors.push('Servos must be an object mapping servo indices to PWM values');
    } else {
      // Check that we have exactly 6 servos (indices 1-6)
      const servoIndices = Object.keys(frame.servos).map(Number).sort();
      const expectedIndices = [1, 2, 3, 4, 5, 6];
      
      if (servoIndices.length !== 6) {
        errors.push(`Must have exactly 6 servo positions (indices 1-6), got ${servoIndices.length} servos`);
      } else if (!servoIndices.every((index, i) => index === expectedIndices[i])) {
        errors.push(`Servo indices must be 1-6, got indices: ${servoIndices.join(', ')}`);
      }
      
      // Validate each PWM value
      Object.entries(frame.servos).forEach(([index, pwm]) => {
        const servoIndex = Number(index);
        if (typeof pwm !== 'number') {
          errors.push(`Servo ${servoIndex} PWM must be a number, got ${typeof pwm}`);
        } else if (pwm < 500 || pwm > 2500) {
          errors.push(`Servo ${servoIndex} PWM must be between 500-2500 microseconds for safe operation, got ${pwm}µs`);
        }
      });
    }
    
    // Validate optional soundId
    if (frame.soundId !== undefined) {
      if (typeof frame.soundId !== 'number') {
        errors.push(`Sound ID must be a number, got ${typeof frame.soundId}`);
      } else if (frame.soundId < 1 || frame.soundId > 255) {
        errors.push(`Sound ID must be between 1-255 for MP3 module compatibility, got ${frame.soundId}`);
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validates an ActionProject with comprehensive error messages
   */
  static validateProject(project: ActionProject): ValidationResult {
    const errors: string[] = [];
    
    // Validate ID
    if (!project.id || typeof project.id !== 'string') {
      errors.push('Project ID must be a non-empty string');
    } else if (project.id.length === 0) {
      errors.push('Project ID cannot be empty');
    }
    
    // Validate name
    if (!project.name || typeof project.name !== 'string') {
      errors.push('Project name must be a non-empty string');
    } else {
      if (project.name.length === 0) {
        errors.push('Project name cannot be empty');
      } else if (project.name.length > 50) {
        errors.push(`Project name must be 50 characters or less for database compatibility, got ${project.name.length} characters`);
      }
      
      // Check for invalid characters that could cause file system issues
      const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
      if (invalidChars.test(project.name)) {
        errors.push('Project name contains invalid characters. Avoid: < > : " / \\ | ? * and control characters');
      }
    }
    
    // Validate optional remoteSlotId
    if (project.remoteSlotId !== undefined) {
      if (typeof project.remoteSlotId !== 'number') {
        errors.push(`Remote slot ID must be a number, got ${typeof project.remoteSlotId}`);
      } else if (project.remoteSlotId < 1 || project.remoteSlotId > 10) {
        errors.push(`Remote slot ID must be between 1-10 for Arduino EEPROM slots, got ${project.remoteSlotId}`);
      }
    }
    
    // Validate frames array
    if (!Array.isArray(project.frames)) {
      errors.push('Project frames must be an array');
    } else {
      // Validate each frame
      project.frames.forEach((frame, index) => {
        const frameValidation = this.validateFrame(frame);
        if (!frameValidation.isValid) {
          frameValidation.errors.forEach(error => {
            errors.push(`Frame ${index}: ${error}`);
          });
        }
      });
      
      // Validate sequence IDs are consecutive
      if (project.frames.length > 0) {
        const sequenceIds = project.frames.map(f => f.sequenceId).sort((a, b) => a - b);
        const expectedIds = Array.from({ length: project.frames.length }, (_, i) => i);
        
        if (!sequenceIds.every((id, index) => id === expectedIds[index])) {
          errors.push(`Frame sequence IDs must be consecutive starting from 0, got: ${sequenceIds.join(', ')}`);
        }
      }
    }
    
    // Validate timestamps
    if (typeof project.createdAt !== 'number' || project.createdAt <= 0) {
      errors.push('Created timestamp must be a positive number');
    }
    
    if (typeof project.modifiedAt !== 'number' || project.modifiedAt <= 0) {
      errors.push('Modified timestamp must be a positive number');
    }
    
    if (project.createdAt > project.modifiedAt) {
      errors.push('Created timestamp cannot be after modified timestamp');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validates PWM value with detailed error message
   */
  static validatePWM(pwm: number, servoIndex?: number): ValidationResult {
    const errors: string[] = [];
    const servoLabel = servoIndex ? `Servo ${servoIndex}` : 'PWM value';
    
    if (typeof pwm !== 'number') {
      errors.push(`${servoLabel} must be a number, got ${typeof pwm}`);
    } else if (!Number.isFinite(pwm)) {
      errors.push(`${servoLabel} must be a finite number, got ${pwm}`);
    } else if (pwm < 500 || pwm > 2500) {
      errors.push(`${servoLabel} must be between 500-2500 microseconds for safe servo operation, got ${pwm}µs`);
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validates duration with detailed error message
   */
  static validateDuration(duration: number): ValidationResult {
    const errors: string[] = [];
    
    if (typeof duration !== 'number') {
      errors.push(`Duration must be a number, got ${typeof duration}`);
    } else if (!Number.isFinite(duration)) {
      errors.push(`Duration must be a finite number, got ${duration}`);
    } else if (duration < 500 || duration > 5000) {
      errors.push(`Duration must be between 500-5000ms for safe servo operation, got ${duration}ms`);
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validates sound ID with detailed error message
   */
  static validateSoundId(soundId: number): ValidationResult {
    const errors: string[] = [];
    
    if (typeof soundId !== 'number') {
      errors.push(`Sound ID must be a number, got ${typeof soundId}`);
    } else if (!Number.isInteger(soundId)) {
      errors.push(`Sound ID must be an integer, got ${soundId}`);
    } else if (soundId < 1 || soundId > 255) {
      errors.push(`Sound ID must be between 1-255 for MP3 module compatibility, got ${soundId}`);
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
  
  /**
   * Validates project name with detailed error message
   */
  static validateProjectName(name: string): ValidationResult {
    const errors: string[] = [];
    
    if (typeof name !== 'string') {
      errors.push(`Project name must be a string, got ${typeof name}`);
    } else {
      if (name.length === 0) {
        errors.push('Project name cannot be empty');
      } else if (name.length > 50) {
        errors.push(`Project name must be 50 characters or less for database compatibility, got ${name.length} characters`);
      }
      
      // Check for invalid characters
      const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
      if (invalidChars.test(name)) {
        errors.push('Project name contains invalid characters. Avoid: < > : " / \\ | ? * and control characters');
      }
      
      // Check for reserved Windows names
      const reservedNames = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'];
      if (reservedNames.includes(name.toUpperCase())) {
        errors.push(`Project name "${name}" is a reserved Windows filename and cannot be used`);
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
}