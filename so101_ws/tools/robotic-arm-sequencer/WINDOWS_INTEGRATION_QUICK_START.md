# Windows Integration Quick Start Guide

## Quick Reference for Developers

### Using Windows Integration Features in Your Code

#### 1. Theme Detection

```typescript
// Get current Windows theme
const theme = await window.electronAPI.getTheme();
console.log('Dark mode:', theme.shouldUseDarkColors);

// Listen for theme changes
window.electronAPI.on.themeChanged((theme) => {
  if (theme.shouldUseDarkColors) {
    // Apply dark theme
  } else {
    // Apply light theme
  }
});
```

#### 2. System Tray Status Updates

```typescript
// Update tray status when connection changes
await window.electronAPI.updateTrayStatus('connected');
await window.electronAPI.updateTrayStatus('disconnected');
await window.electronAPI.updateTrayStatus('executing');
```

#### 3. Menu Command Handlers

```typescript
// Listen for menu shortcuts
window.electronAPI.on.menuNewProject(() => {
  // Handle new project
});

window.electronAPI.on.menuSaveProject(() => {
  // Handle save project
});

window.electronAPI.on.menuUndo(() => {
  // Handle undo
});

window.electronAPI.on.menuRedo(() => {
  // Handle redo
});
```

#### 4. File Open Handler

```typescript
// Handle files opened via double-click
window.electronAPI.on.fileOpened((project) => {
  // Load the project
  console.log('Opening project:', project.name);
});
```

### Building for Windows

```bash
# Install dependencies (first time only)
npm install

# Build the application
npm run build

# Create Windows installer
npm run dist:win

# Create portable version
npm run pack

# Test in development
npm run electron:dev
```

### Output Files

After building, find your installers in:
```
release/
  ├── Robotic Arm Sequencer Setup 1.0.0.exe  (Installer)
  └── Robotic Arm Sequencer-1.0.0-Portable.exe  (Portable)
```

### Icon Files Needed

Place these files in the `build/` directory:

1. **icon.ico** - Main app icon (256x256)
2. **file-icon.ico** - .armseq file icon
3. **installer-icon.ico** - Installer icon
4. **uninstaller-icon.ico** - Uninstaller icon

Place these files in `src/renderer/assets/`:

5. **tray-icon.png** - System tray icon (16x16)
6. **tray-icon-dark.png** - Dark theme tray
7. **tray-icon-light.png** - Light theme tray
8. **app-icon.png** - Window icon (256x256)

### Testing Checklist

- [ ] Build installer: `npm run dist:win`
- [ ] Install on clean Windows machine
- [ ] Double-click .armseq file - opens in app
- [ ] Check system tray icon appears
- [ ] Test keyboard shortcuts (Ctrl+S, Ctrl+Z, etc.)
- [ ] Close and reopen - window position restored
- [ ] Change Windows theme - app receives notification
- [ ] Right-click tray icon - menu appears
- [ ] Click tray icon - window shows/hides

### Common Issues

**Icons not showing:**
- Create icon files in `build/` directory
- See `build/README.md` for specifications

**File associations not working:**
- Reinstall the application
- Check Windows Default Apps settings

**Tray icon missing:**
- Create tray icon files in `src/renderer/assets/`
- Check file paths in main.ts

**Shortcuts not working:**
- Check if another app uses the same shortcut
- Verify menu is created in main.ts

### API Reference

**IPC Methods:**
```typescript
window.electronAPI.getTheme()
window.electronAPI.updateTrayStatus(status)
```

**Event Listeners:**
```typescript
window.electronAPI.on.themeChanged(callback)
window.electronAPI.on.fileOpened(callback)
window.electronAPI.on.menuNewProject(callback)
window.electronAPI.on.menuSaveProject(callback)
window.electronAPI.on.menuSaveProjectAs(callback)
window.electronAPI.on.menuImportProject(callback)
window.electronAPI.on.menuExportProject(callback)
window.electronAPI.on.menuUndo(callback)
window.electronAPI.on.menuRedo(callback)
```

### File Locations

**User Data:**
```
%APPDATA%/robotic-arm-sequencer/
  ├── robotic-arm-sequencer.db  (Database)
  └── window-state.json          (Window state)
```

**Installation:**
```
%LOCALAPPDATA%/Programs/robotic-arm-sequencer/
```

### Documentation

- **WINDOWS_INTEGRATION.md** - Complete feature documentation
- **WINDOWS_INTEGRATION_IMPLEMENTATION.md** - Implementation details
- **build/README.md** - Icon specifications

### Support

For issues or questions:
1. Check the documentation files
2. Review test files in `src/__tests__/windows-integration.test.ts`
3. Check Electron documentation: https://www.electronjs.org/docs

---

**Quick Start Complete!** You're ready to use Windows integration features.
