# Windows Integration Features

This document describes the Windows-specific integration features implemented in the Robotic Arm Sequencer application.

## Features Overview

### 1. File Associations (.armseq files)

The application registers itself as the default handler for `.armseq` files.

**Features:**
- Double-clicking a `.armseq` file opens it in the application
- Custom file icon in Windows Explorer
- Right-click context menu integration
- "Open with" menu support

**Implementation:**
- Configured in `package.json` under `build.win.fileAssociations`
- Protocol handler registered in `main.ts` via `app.setAsDefaultProtocolClient()`
- File open events handled via `app.on('open-file')` event

**Usage:**
```typescript
// Files opened via double-click are sent to the renderer
app.on('open-file', async (event, filePath) => {
  event.preventDefault();
  await this.handleFileOpen(filePath);
});
```

### 2. System Tray Integration

The application provides a system tray icon with status indicators.

**Features:**
- Persistent tray icon showing connection status
- Context menu with quick actions
- Click to show/hide main window
- Status updates: Connected, Disconnected, Executing

**Implementation:**
- Created in `createSystemTray()` method
- Updated via `updateTrayMenu()` method
- Renderer can update status via `app:updateTrayStatus` IPC call

**Tray Menu Options:**
- Show Window
- Hide Window
- Status indicator (read-only)
- Quit application

**Usage:**
```typescript
// Update tray status from renderer
await window.electronAPI.updateTrayStatus('connected');
```

### 3. Keyboard Shortcuts

Global keyboard shortcuts for common operations.

**File Operations:**
- `Ctrl+N` - New Project
- `Ctrl+O` - Open Project
- `Ctrl+S` - Save Project
- `Ctrl+Shift+S` - Save Project As
- `Ctrl+E` - Export Project

**Edit Operations:**
- `Ctrl+Z` - Undo
- `Ctrl+Shift+Z` - Redo
- `Ctrl+X` - Cut
- `Ctrl+C` - Copy
- `Ctrl+V` - Paste

**Implementation:**
- Configured in `createApplicationMenu()` method
- Menu items send IPC events to renderer
- Renderer listens via `window.electronAPI.on.*` methods

**Usage:**
```typescript
// Listen for menu shortcuts in renderer
window.electronAPI.on.menuSaveProject(() => {
  // Handle save project
});
```

### 4. Window State Persistence

The application remembers window position, size, and maximized state.

**Features:**
- Window position (x, y coordinates)
- Window size (width, height)
- Maximized state
- Restored on application restart

**Implementation:**
- State saved to `window-state.json` in user data directory
- Loaded on startup via `loadWindowState()`
- Saved on window events: resize, move, maximize, unmaximize

**Storage Location:**
```
%APPDATA%/robotic-arm-sequencer/window-state.json
```

**State Format:**
```json
{
  "x": 100,
  "y": 100,
  "width": 1400,
  "height": 900,
  "isMaximized": false
}
```

### 5. Dark/Light Theme Detection

The application detects and responds to Windows theme changes.

**Features:**
- Automatic detection of Windows dark/light mode
- High contrast mode detection
- Real-time theme change notifications
- Theme information available to renderer

**Implementation:**
- Uses Electron's `nativeTheme` API
- Listens for `nativeTheme.on('updated')` events
- Sends theme changes to renderer via IPC

**Theme Properties:**
- `shouldUseDarkColors` - Windows is in dark mode
- `shouldUseHighContrastColors` - High contrast mode enabled
- `shouldUseInvertedColorScheme` - Inverted colors enabled

**Usage:**
```typescript
// Get current theme in renderer
const theme = await window.electronAPI.getTheme();
console.log('Dark mode:', theme.shouldUseDarkColors);

// Listen for theme changes
window.electronAPI.on.themeChanged((theme) => {
  console.log('Theme changed:', theme);
  // Update UI accordingly
});
```

### 6. Windows Installer Configuration

Professional installer with NSIS (Nullsoft Scriptable Install System).

**Features:**
- Custom installation directory selection
- Desktop shortcut creation
- Start menu shortcut creation
- File association registration
- Uninstaller with proper cleanup
- Portable version (no installation required)

**Build Targets:**
- **NSIS Installer** - Traditional Windows installer (.exe)
- **Portable** - Standalone executable (no installation)

**Build Commands:**
```bash
# Build installer for Windows
npm run dist:win

# Build portable version
npm run pack

# Build all platforms
npm run dist
```

**Installer Features:**
- One-click or custom installation
- Per-user installation (no admin required)
- Automatic file association setup
- Custom icons for installer/uninstaller
- License agreement display

**Output Location:**
```
release/
  ├── Robotic Arm Sequencer Setup 1.0.0.exe  (Installer)
  └── Robotic Arm Sequencer-1.0.0-Portable.exe  (Portable)
```

## IPC API Reference

### App Methods

```typescript
// Get application version
const version = await window.electronAPI.getVersion();

// Get current Windows theme
const theme = await window.electronAPI.getTheme();

// Update system tray status
await window.electronAPI.updateTrayStatus('connected');
```

### Event Listeners

```typescript
// Theme changed
window.electronAPI.on.themeChanged((theme) => {
  // Handle theme change
});

// File opened via double-click
window.electronAPI.on.fileOpened((project) => {
  // Load the project
});

// Menu shortcuts
window.electronAPI.on.menuNewProject(() => { /* ... */ });
window.electronAPI.on.menuSaveProject(() => { /* ... */ });
window.electronAPI.on.menuSaveProjectAs(() => { /* ... */ });
window.electronAPI.on.menuImportProject(() => { /* ... */ });
window.electronAPI.on.menuExportProject(() => { /* ... */ });
window.electronAPI.on.menuUndo(() => { /* ... */ });
window.electronAPI.on.menuRedo(() => { /* ... */ });
```

## User Data Locations

The application stores data in standard Windows locations:

**User Data Directory:**
```
%APPDATA%/robotic-arm-sequencer/
```

**Files:**
- `robotic-arm-sequencer.db` - SQLite database
- `window-state.json` - Window state persistence
- `logs/` - Application logs (if logging enabled)

## Testing Windows Integration

### File Associations

1. Build the application: `npm run dist:win`
2. Install the application
3. Create a test `.armseq` file
4. Double-click the file - should open in the application

### System Tray

1. Run the application
2. Check system tray for the application icon
3. Right-click the icon to see the context menu
4. Click the icon to show/hide the window

### Keyboard Shortcuts

1. Run the application
2. Press `Ctrl+N` - should trigger new project
3. Press `Ctrl+S` - should trigger save project
4. Press `Ctrl+Z` - should trigger undo

### Window State

1. Run the application
2. Move and resize the window
3. Close the application
4. Reopen - window should be in the same position and size

### Theme Detection

1. Run the application
2. Change Windows theme (Settings > Personalization > Colors)
3. Application should receive theme change event

## Troubleshooting

### File Associations Not Working

- Reinstall the application
- Check Windows Default Apps settings
- Manually set default program for `.armseq` files

### System Tray Icon Not Showing

- Check if tray icon files exist in `src/renderer/assets/`
- Verify icon paths in `main.ts`
- Check Windows system tray settings

### Keyboard Shortcuts Not Working

- Check if another application is using the same shortcuts
- Verify menu is properly created in `createApplicationMenu()`
- Check IPC event listeners in renderer

### Window State Not Persisting

- Check if `window-state.json` is being created
- Verify write permissions to user data directory
- Check for errors in console logs

## Future Enhancements

Potential improvements for Windows integration:

1. **Jump List Support** - Recent projects in taskbar jump list
2. **Thumbnail Toolbar** - Playback controls in taskbar preview
3. **Progress Bar** - Show download progress in taskbar
4. **Notifications** - Windows 10/11 toast notifications
5. **Touch Support** - Touch gestures for Windows tablets
6. **Windows Hello** - Biometric authentication for sensitive operations
7. **Cortana Integration** - Voice commands for basic operations

## Requirements Validation

This implementation satisfies the following requirements:

- **11.1** ✓ Windows installer (.msi or .exe) via electron-builder
- **11.2** ✓ File associations for .armseq files
- **11.3** ✓ Double-click to open .armseq files
- **11.5** ✓ Windows keyboard shortcuts (Ctrl+S, Ctrl+Z, etc.)
- **11.6** ✓ Window position and size persistence
- **11.7** ✓ Windows dark/light theme detection

Additional features implemented:
- System tray integration (11.4)
- Application menu with shortcuts
- File protocol handler
- Professional NSIS installer
- Portable version support
