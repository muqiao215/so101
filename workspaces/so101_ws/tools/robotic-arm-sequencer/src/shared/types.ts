// Domain Models
export interface ActionFrame {
  sequenceId: number;
  duration: number;  // milliseconds, clamped to 500-5000
  servos: Record<number, number>;  // servo index (1-6) to PWM (500-2500)
  soundId?: number;  // MP3 track ID (1-255)
}

export interface ActionProject {
  id: string;  // UUID
  name: string;  // max 50 characters
  remoteSlotId?: number;  // 1-10 for Arduino storage
  frames: ActionFrame[];
  createdAt: number;  // timestamp
  modifiedAt: number;  // timestamp
}

// Execution Types
export interface ExecutionOptions {
  loop: boolean;
  onProgress?: (progress: ExecutionProgress) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

export interface ExecutionProgress {
  currentFrame: number;
  totalFrames: number;
  percentage: number;
}

export type ExecutionState = 'idle' | 'running' | 'paused' | 'stopped' | 'error';

// MP3 Command Types
export type Mp3Command = 
  | { type: 'play'; trackId: number }
  | { type: 'stop' }
  | { type: 'next' }
  | { type: 'previous' }
  | { type: 'volume'; level: number };  // 0-30

// Serial Port Types
export interface PortInfo {
  path: string;
  manufacturer?: string;
  serialNumber?: string;
  pnpId?: string;
  locationId?: string;
  productId?: string;
  vendorId?: string;
}

// Database Schema Types
export interface ProjectEntity {
  id: string;
  name: string;
  remote_slot_id?: number;
  created_at: number;
  modified_at: number;
}

export interface FrameEntity {
  id: string;
  project_id: string;
  sequence_id: number;
  duration: number;
  servo1: number;
  servo2: number;
  servo3: number;
  servo4: number;
  servo5: number;
  servo6: number;
  sound_id?: number;
}

// Validation Types
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// Error Types
export class SerialError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SerialError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class DatabaseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DatabaseError';
  }
}

export class DuplicateProjectError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DuplicateProjectError';
  }
}