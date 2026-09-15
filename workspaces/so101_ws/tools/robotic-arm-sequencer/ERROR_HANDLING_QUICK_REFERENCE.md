# Error Handling Quick Reference

## Quick Start

### 1. Show a Toast Notification

```typescript
import { useNotifications } from '../contexts/NotificationContext';

const MyComponent = () => {
  const { showSuccess, showError, showWarning, showInfo } = useNotifications();
  
  // Success
  showSuccess('Saved', 'Project saved successfully');
  
  // Error
  showError(ERROR_MESSAGES.SERIAL_CONNECTION_LOST);
  
  // Warning
  showWarning('Warning', 'Frame duration may be too short');
  
  // Info
  showInfo('Connected', 'Connected to Arduino on COM3');
};
```

### 2. Show an Error Dialog

```typescript
import ErrorDialog from './ErrorDialog';
import { mapErrorToAppError } from '../../shared/error-types';

const [showDialog, setShowDialog] = useState(false);
const [error, setError] = useState(null);

try {
  await riskyOperation();
} catch (err) {
  setError(mapErrorToAppError(err));
  setShowDialog(true);
}

// Render
{showDialog && error && (
  <ErrorDialog
    error={error}
    onClose={() => setShowDialog(false)}
    onRetry={() => retryOperation()}
  />
)}
```

### 3. Show a Warning Dialog

```typescript
import WarningDialog from './WarningDialog';

<WarningDialog
  title="Delete Project"
  message="Are you sure?"
  onConfirm={handleDelete}
  onCancel={() => setShowWarning(false)}
  dangerous
/>
```

### 4. Display Connection Status

```typescript
import ConnectionStatus from './ConnectionStatus';

<ConnectionStatus 
  state={connectionState} 
  portName="COM3" 
/>
```

### 5. Show Validation Error

```typescript
import ValidationError from './ValidationError';

<ValidationError
  message="Invalid PWM value"
  guidance="Value must be between 500-2500"
/>
```

## Error Categories

| Category | Use For | Example |
|----------|---------|---------|
| VALIDATION | Input validation errors | Invalid PWM, duration, name |
| SERIAL | Serial communication errors | Connection lost, timeout |
| DATABASE | Database operation errors | Save failed, load failed |
| FILE_SYSTEM | File operation errors | Import failed, invalid JSON |
| EXECUTION | Sequence execution errors | Download failed, MP3 error |

## Predefined Errors

```typescript
import { ERROR_MESSAGES } from '../../shared/error-types';

// Validation
ERROR_MESSAGES.INVALID_PWM
ERROR_MESSAGES.INVALID_DURATION
ERROR_MESSAGES.INVALID_SOUND_ID
ERROR_MESSAGES.INVALID_PROJECT_NAME
ERROR_MESSAGES.SEQUENCE_TOO_LARGE

// Serial
ERROR_MESSAGES.SERIAL_NOT_CONNECTED
ERROR_MESSAGES.SERIAL_CONNECTION_LOST
ERROR_MESSAGES.SERIAL_TIMEOUT
ERROR_MESSAGES.CHECKSUM_MISMATCH

// Database
ERROR_MESSAGES.DATABASE_WRITE_ERROR
ERROR_MESSAGES.DATABASE_READ_ERROR
ERROR_MESSAGES.DUPLICATE_PROJECT

// File System
ERROR_MESSAGES.FILE_NOT_FOUND
ERROR_MESSAGES.INVALID_JSON

// Execution
ERROR_MESSAGES.EXECUTION_FAILED
ERROR_MESSAGES.DOWNLOAD_FAILED
ERROR_MESSAGES.MP3_COMMAND_FAILED
```

## Connection States

```typescript
type ConnectionState = 'connected' | 'disconnected' | 'connecting' | 'error';
```

| State | Color | Icon | Animation |
|-------|-------|------|-----------|
| connected | Green | ● | None |
| disconnected | Gray | ○ | None |
| connecting | Yellow | ◐ | Spin |
| error | Neon Magenta | ✕ | Pulse |

## Notification Types

| Type | Color | Icon | Duration | Use For |
|------|-------|------|----------|---------|
| success | Green | ✓ | 4s | Successful operations |
| error | Neon Magenta | ✕ | 7s | Errors and failures |
| warning | Yellow | ⚠ | 6s | Warnings and cautions |
| info | Industrial Steel Blue | ℹ | 5s | Information and status |

## Error Logging

```typescript
import { logError } from '../../shared/error-types';

try {
  await operation();
} catch (error) {
  logError(error, 'Operation context');
  // Logs to console with timestamp, category, code, message, stack
}
```

## Common Patterns

### Handle IPC Errors

```typescript
try {
  await window.electronAPI.project.save(project);
  showSuccess('Saved', 'Project saved successfully');
} catch (error) {
  logError(error, 'Project save');
  showError(mapErrorToAppError(error));
}
```

### Validate Before Submit

```typescript
const result = ValidationService.validateFrame(frame);
if (!result.isValid) {
  showError({
    category: 'VALIDATION',
    code: 'INVALID_FRAME',
    message: 'Invalid frame data',
    userGuidance: result.errors.join(', '),
    recoverable: true
  });
  return;
}
```

### Confirm Dangerous Action

```typescript
const handleDelete = () => {
  setWarningDialog({
    title: 'Delete Project',
    message: 'This action cannot be undone',
    onConfirm: async () => {
      try {
        await deleteProject();
        showSuccess('Deleted', 'Project deleted');
      } catch (error) {
        showError(mapErrorToAppError(error));
      }
    }
  });
  setShowWarning(true);
};
```

## Testing

```bash
# Run error handling tests
npm test -- error-handling.test.tsx --run

# View showcase
npm start -- --showcase=true
```

## Files

- `src/shared/error-types.ts` - Error definitions and mapping
- `src/renderer/contexts/NotificationContext.tsx` - Notification context
- `src/renderer/components/ToastNotification.tsx` - Toast component
- `src/renderer/components/ErrorDialog.tsx` - Error dialog
- `src/renderer/components/WarningDialog.tsx` - Warning dialog
- `src/renderer/components/ConnectionStatus.tsx` - Connection status
- `src/renderer/components/ValidationError.tsx` - Validation error
- `src/__tests__/error-handling.test.tsx` - Tests

## Documentation

See `ERROR_HANDLING_README.md` for complete documentation.
