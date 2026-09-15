// Error Types and User-Friendly Mappings

export enum ErrorCategory {
  VALIDATION = 'VALIDATION',
  SERIAL = 'SERIAL',
  DATABASE = 'DATABASE',
  FILE_SYSTEM = 'FILE_SYSTEM',
  EXECUTION = 'EXECUTION',
  UNKNOWN = 'UNKNOWN'
}

export interface AppError {
  category: ErrorCategory;
  code: string;
  message: string;
  technicalDetails?: string;
  userGuidance?: string;
  recoverable: boolean;
}

// User-friendly error mapping
export const ERROR_MESSAGES: Record<string, AppError> = {
  // Validation Errors
  'INVALID_PWM': {
    category: ErrorCategory.VALIDATION,
    code: 'INVALID_PWM',
    message: 'Invalid servo position value',
    userGuidance: 'Servo PWM values must be between 500-2500 microseconds. The value has been automatically adjusted to the valid range.',
    recoverable: true
  },
  'INVALID_DURATION': {
    category: ErrorCategory.VALIDATION,
    code: 'INVALID_DURATION',
    message: 'Invalid frame duration',
    userGuidance: 'Frame duration must be between 500-5000 milliseconds. The value has been automatically adjusted to the valid range.',
    recoverable: true
  },
  'INVALID_SOUND_ID': {
    category: ErrorCategory.VALIDATION,
    code: 'INVALID_SOUND_ID',
    message: 'Invalid MP3 track ID',
    userGuidance: 'MP3 track IDs must be between 1-255. Please select a valid track number.',
    recoverable: true
  },
  'INVALID_PROJECT_NAME': {
    category: ErrorCategory.VALIDATION,
    code: 'INVALID_PROJECT_NAME',
    message: 'Invalid project name',
    userGuidance: 'Project names must be 1-50 characters and cannot contain special characters like / \\ : * ? " < > |',
    recoverable: true
  },
  'SEQUENCE_TOO_LARGE': {
    category: ErrorCategory.VALIDATION,
    code: 'SEQUENCE_TOO_LARGE',
    message: 'Sequence exceeds Arduino EEPROM capacity',
    userGuidance: 'The sequence is too large to fit in Arduino memory. Please reduce the number of frames or split into multiple sequences.',
    recoverable: true
  },
  'FRAME_DURATION_WARNING': {
    category: ErrorCategory.VALIDATION,
    code: 'FRAME_DURATION_WARNING',
    message: 'Frame duration may be too short',
    userGuidance: 'The frame duration is very short and servos may not complete their movement. Consider increasing the duration for smoother motion.',
    recoverable: true
  },

  // Serial Communication Errors
  'SERIAL_NOT_CONNECTED': {
    category: ErrorCategory.SERIAL,
    code: 'SERIAL_NOT_CONNECTED',
    message: 'Serial port not connected',
    userGuidance: 'Please connect to the Arduino via the serial port before executing commands.',
    recoverable: true
  },
  'SERIAL_CONNECTION_LOST': {
    category: ErrorCategory.SERIAL,
    code: 'SERIAL_CONNECTION_LOST',
    message: 'Serial connection lost',
    userGuidance: 'The connection to the Arduino was lost. Please check the USB cable and reconnect.',
    recoverable: true
  },
  'SERIAL_TIMEOUT': {
    category: ErrorCategory.SERIAL,
    code: 'SERIAL_TIMEOUT',
    message: 'Command timeout',
    userGuidance: 'The Arduino did not respond within the expected time. Please check the connection and try again.',
    recoverable: true
  },
  'SERIAL_WRITE_ERROR': {
    category: ErrorCategory.SERIAL,
    code: 'SERIAL_WRITE_ERROR',
    message: 'Failed to send command',
    userGuidance: 'Could not send command to Arduino. Please check the connection and try again.',
    recoverable: true
  },
  'CHECKSUM_MISMATCH': {
    category: ErrorCategory.SERIAL,
    code: 'CHECKSUM_MISMATCH',
    message: 'Data corruption detected',
    userGuidance: 'The data received from Arduino was corrupted. The system will automatically retry.',
    recoverable: true
  },

  // Database Errors
  'DATABASE_CONNECTION_ERROR': {
    category: ErrorCategory.DATABASE,
    code: 'DATABASE_CONNECTION_ERROR',
    message: 'Database connection failed',
    userGuidance: 'Could not connect to the local database. Please restart the application.',
    recoverable: false
  },
  'DATABASE_WRITE_ERROR': {
    category: ErrorCategory.DATABASE,
    code: 'DATABASE_WRITE_ERROR',
    message: 'Failed to save data',
    userGuidance: 'Could not save changes to the database. Please check disk space and try again.',
    recoverable: true
  },
  'DATABASE_READ_ERROR': {
    category: ErrorCategory.DATABASE,
    code: 'DATABASE_READ_ERROR',
    message: 'Failed to load data',
    userGuidance: 'Could not load data from the database. The database file may be corrupted.',
    recoverable: false
  },
  'DUPLICATE_PROJECT': {
    category: ErrorCategory.DATABASE,
    code: 'DUPLICATE_PROJECT',
    message: 'Project already exists',
    userGuidance: 'A project with this ID already exists. Please try again or contact support if the issue persists.',
    recoverable: true
  },

  // File System Errors
  'FILE_NOT_FOUND': {
    category: ErrorCategory.FILE_SYSTEM,
    code: 'FILE_NOT_FOUND',
    message: 'File not found',
    userGuidance: 'The selected file could not be found. It may have been moved or deleted.',
    recoverable: true
  },
  'FILE_READ_ERROR': {
    category: ErrorCategory.FILE_SYSTEM,
    code: 'FILE_READ_ERROR',
    message: 'Failed to read file',
    userGuidance: 'Could not read the file. Please check file permissions and try again.',
    recoverable: true
  },
  'FILE_WRITE_ERROR': {
    category: ErrorCategory.FILE_SYSTEM,
    code: 'FILE_WRITE_ERROR',
    message: 'Failed to write file',
    userGuidance: 'Could not save the file. Please check disk space and file permissions.',
    recoverable: true
  },
  'INVALID_JSON': {
    category: ErrorCategory.FILE_SYSTEM,
    code: 'INVALID_JSON',
    message: 'Invalid file format',
    userGuidance: 'The file is not a valid .armseq project file. Please select a valid project file.',
    recoverable: true
  },

  // Execution Errors
  'EXECUTION_FAILED': {
    category: ErrorCategory.EXECUTION,
    code: 'EXECUTION_FAILED',
    message: 'Sequence execution failed',
    userGuidance: 'The sequence could not be executed. Please check the serial connection and try again.',
    recoverable: true
  },
  'DOWNLOAD_FAILED': {
    category: ErrorCategory.EXECUTION,
    code: 'DOWNLOAD_FAILED',
    message: 'Failed to download sequence to Arduino',
    userGuidance: 'Could not download the sequence to Arduino memory. Please check the connection and try again.',
    recoverable: true
  },
  'MP3_COMMAND_FAILED': {
    category: ErrorCategory.EXECUTION,
    code: 'MP3_COMMAND_FAILED',
    message: 'MP3 command failed',
    userGuidance: 'The MP3 module did not respond. Servo execution will continue, but audio may not play.',
    recoverable: true
  }
};

// Helper function to map errors to user-friendly messages
export function mapErrorToAppError(error: Error): AppError {
  // Check if it's a known error type
  const errorCode = error.name.replace('Error', '').toUpperCase();
  
  // Try to find a matching error message
  for (const [key, appError] of Object.entries(ERROR_MESSAGES)) {
    if (error.message.includes(key) || error.name.includes(key) || errorCode.includes(key)) {
      return {
        ...appError,
        technicalDetails: error.message
      };
    }
  }

  // Return generic error
  return {
    category: ErrorCategory.UNKNOWN,
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
    technicalDetails: error.message,
    userGuidance: 'Please try again. If the problem persists, restart the application.',
    recoverable: true
  };
}

// Error logging function
export function logError(error: Error, context?: string): void {
  const timestamp = new Date().toISOString();
  const appError = mapErrorToAppError(error);
  
  console.error(`[${timestamp}] ${context || 'Error'}:`, {
    category: appError.category,
    code: appError.code,
    message: appError.message,
    technicalDetails: appError.technicalDetails,
    stack: error.stack
  });
}
