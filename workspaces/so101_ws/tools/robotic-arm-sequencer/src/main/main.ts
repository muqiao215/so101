import { app, BrowserWindow, ipcMain, dialog, Tray, Menu, nativeTheme, protocol } from 'electron';
import * as path from 'path';
import * as fs from 'fs/promises';
import { SQLiteDatabase } from './database';
import { SerialPortManager } from './serial-port-manager';
import { RoboticArmService } from './robotic-arm-service';
import {
  ActionProject,
  ActionFrame,
  ExecutionOptions,
  Mp3Command,
  PortInfo
} from '../shared/types';

interface WindowState {
  x: number;
  y: number;
  width: number;
  height: number;
  isMaximized: boolean;
}

class MainApplication {
  private mainWindow: BrowserWindow | null = null;
  private service: RoboticArmService | null = null;
  private db: SQLiteDatabase | null = null;
  private serialPort: SerialPortManager | null = null;
  private tray: Tray | null = null;
  private windowState: WindowState | null = null;
  private windowStateFile: string = '';

  constructor() {
    this.initializeApp();
  }

  private initializeApp(): void {
    // Register .armseq file protocol
    this.registerFileProtocol();

    // Handle app ready event
    app.whenReady().then(() => {
      this.initializeServices();
      this.loadWindowState();
      this.createMainWindow();
      this.createSystemTray();
      this.registerGlobalShortcuts();

      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
          this.createMainWindow();
        }
      });
    });

    // Handle window closed events
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    // Cleanup on quit
    app.on('before-quit', async () => {
      await this.cleanup();
    });

    // Handle file open (Windows file association)
    app.on('open-file', async (event, filePath) => {
      event.preventDefault();
      await this.handleFileOpen(filePath);
    });

    // Setup IPC handlers
    this.setupIPCHandlers();
  }

  private initializeServices(): void {
    try {
      // Initialize database
      const dbPath = path.join(app.getPath('userData'), 'robotic-arm-sequencer.db');
      this.db = new SQLiteDatabase(dbPath);

      // Initialize serial port manager
      this.serialPort = new SerialPortManager();

      // Initialize main service
      this.service = new RoboticArmService(this.db, this.serialPort);

      // Set window state file path
      this.windowStateFile = path.join(app.getPath('userData'), 'window-state.json');
    } catch (error) {
      console.error('Failed to initialize services:', error);
      // Don't quit - let the app start with limited functionality
      dialog.showErrorBox('Initialization Warning',
        `Some services failed to initialize. The app will start with limited functionality.\n\nError: ${error}\n\nYou may need to install Visual Studio Build Tools to compile native modules.`);

      // Initialize what we can
      try {
        this.serialPort = new SerialPortManager();
        this.windowStateFile = path.join(app.getPath('userData'), 'window-state.json');
      } catch (e) {
        console.error('Failed to initialize serial port:', e);
      }
    }
  }

  private registerFileProtocol(): void {
    // Set as default protocol client for .armseq files
    if (process.defaultApp) {
      if (process.argv.length >= 2) {
        app.setAsDefaultProtocolClient('armseq', process.execPath, [path.resolve(process.argv[1])]);
      }
    } else {
      app.setAsDefaultProtocolClient('armseq');
    }
  }

  private async handleFileOpen(filePath: string): Promise<void> {
    try {
      if (!filePath.endsWith('.armseq')) {
        return;
      }

      const fileContent = await fs.readFile(filePath, 'utf-8');
      const project: ActionProject = JSON.parse(fileContent);

      // Send to renderer to open the project
      if (this.mainWindow) {
        this.mainWindow.webContents.send('file:opened', project);
      }
    } catch (error) {
      console.error('Failed to open file:', error);
      dialog.showErrorBox('File Open Error', `Failed to open file: ${error}`);
    }
  }

  private async loadWindowState(): Promise<void> {
    try {
      const stateData = await fs.readFile(this.windowStateFile, 'utf-8');
      this.windowState = JSON.parse(stateData);
    } catch (error) {
      // Use default window state if file doesn't exist
      this.windowState = {
        x: undefined as any,
        y: undefined as any,
        width: 1400,
        height: 900,
        isMaximized: false
      };
    }
  }

  private async saveWindowState(): Promise<void> {
    if (!this.mainWindow) return;

    try {
      const bounds = this.mainWindow.getBounds();
      const state: WindowState = {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        isMaximized: this.mainWindow.isMaximized()
      };

      await fs.writeFile(this.windowStateFile, JSON.stringify(state, null, 2), 'utf-8');
    } catch (error) {
      console.error('Failed to save window state:', error);
    }
  }

  private createSystemTray(): void {
    // Try to create tray icon with fallback
    const possiblePaths = [
      path.join(__dirname, '../renderer/assets/tray-icon.png'),
      path.join(__dirname, '../renderer/assets/tray-icon-light.png'),
      path.join(__dirname, '../renderer/assets/tray-icon-dark.png'),
      path.join(__dirname, '../../build/icon.png'),
      path.join(process.resourcesPath, 'icon.png')
    ];

    let trayCreated = false;
    for (const iconPath of possiblePaths) {
      try {
        this.tray = new Tray(iconPath);
        trayCreated = true;
        break;
      } catch (error) {
        // Try next path
        continue;
      }
    }

    if (!trayCreated) {
      console.warn('Could not create tray icon - no valid icon file found');
      // Skip tray creation if no icon is available
      return;
    }

    if (this.tray) {
      this.updateTrayMenu('disconnected');

      this.tray.setToolTip('Robotic Arm Sequencer');

      // Show/hide window on tray click
      this.tray.on('click', () => {
        if (this.mainWindow) {
          if (this.mainWindow.isVisible()) {
            this.mainWindow.hide();
          } else {
            this.mainWindow.show();
          }
        }
      });
    }
  }

  private updateTrayMenu(connectionStatus: 'connected' | 'disconnected' | 'executing'): void {
    if (!this.tray) return;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `Status: ${connectionStatus.toUpperCase()}`,
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Show Window',
        click: () => {
          if (this.mainWindow) {
            this.mainWindow.show();
            this.mainWindow.focus();
          }
        }
      },
      {
        label: 'Hide Window',
        click: () => {
          if (this.mainWindow) {
            this.mainWindow.hide();
          }
        }
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          app.quit();
        }
      }
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  private registerGlobalShortcuts(): void {
    // Note: Global shortcuts are registered via the menu in createMainWindow
    // This method is a placeholder for any additional global shortcuts
  }

  private async cleanup(): Promise<void> {
    try {
      // Save window state before closing
      await this.saveWindowState();

      if (this.service) {
        await this.service.close();
      }

      // Destroy tray icon
      if (this.tray) {
        this.tray.destroy();
      }
    } catch (error) {
      console.error('Cleanup error:', error);
    }
  }

  private createMainWindow(): void {
    const state = this.windowState || {
      x: undefined,
      y: undefined,
      width: 1400,
      height: 900,
      isMaximized: false
    };

    const preloadPath = path.join(__dirname, 'preload.js');
    console.log('=== DEBUG: Preload path ===');
    console.log('__dirname:', __dirname);
    console.log('preload path:', preloadPath);

    // Check if preload file exists
    const fs = require('fs');
    if (fs.existsSync(preloadPath)) {
      console.log('✓ Preload file exists!');
    } else {
      console.error('✗ ERROR: Preload file NOT FOUND at:', preloadPath);
    }

    this.mainWindow = new BrowserWindow({
      x: state.x,
      y: state.y,
      width: state.width,
      height: state.height,
      minWidth: 1200,
      minHeight: 800,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false, // Disable sandbox to fix iterator error
        preload: path.join(__dirname, 'preload.js')
      },
      titleBarStyle: 'default',
      backgroundColor: '#0D0D0D', // Deep Space Black
      show: false,
      icon: path.join(__dirname, '../renderer/assets/app-icon.png')
    });

    // Restore maximized state
    if (state.isMaximized) {
      this.mainWindow.maximize();
    }

    // Create application menu with keyboard shortcuts
    this.createApplicationMenu();

    // Load the renderer
    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadURL('http://localhost:8080');
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    }

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show();
    });

    // Save window state on resize/move
    this.mainWindow.on('resize', () => {
      this.saveWindowState();
    });

    this.mainWindow.on('move', () => {
      this.saveWindowState();
    });

    this.mainWindow.on('maximize', () => {
      this.saveWindowState();
    });

    this.mainWindow.on('unmaximize', () => {
      this.saveWindowState();
    });

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Listen for theme changes
    nativeTheme.on('updated', () => {
      if (this.mainWindow) {
        this.mainWindow.webContents.send('theme:changed', {
          shouldUseDarkColors: nativeTheme.shouldUseDarkColors,
          shouldUseHighContrastColors: nativeTheme.shouldUseHighContrastColors
        });
      }
    });
  }

  private createApplicationMenu(): void {
    const isMac = process.platform === 'darwin';

    const template: any[] = [
      // App Menu (Mac only)
      ...(isMac ? [{
        label: app.name,
        submenu: [
          { role: 'about' },
          { type: 'separator' },
          { role: 'services' },
          { type: 'separator' },
          { role: 'hide' },
          { role: 'hideOthers' },
          { role: 'unhide' },
          { type: 'separator' },
          { role: 'quit' }
        ]
      }] : []),
      // File Menu
      {
        label: 'File',
        submenu: [
          {
            label: 'New Project',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              this.mainWindow?.webContents.send('menu:new-project');
            }
          },
          {
            label: 'Open Project',
            accelerator: 'CmdOrCtrl+O',
            click: async () => {
              const result = await dialog.showOpenDialog({
                filters: [
                  { name: 'Arm Sequence Files', extensions: ['armseq'] },
                  { name: 'JSON Files', extensions: ['json'] }
                ],
                properties: ['openFile']
              });

              if (!result.canceled && result.filePaths[0]) {
                await this.handleFileOpen(result.filePaths[0]);
              }
            }
          },
          {
            label: 'Save Project',
            accelerator: 'CmdOrCtrl+S',
            click: () => {
              this.mainWindow?.webContents.send('menu:save-project');
            }
          },
          {
            label: 'Save Project As...',
            accelerator: 'CmdOrCtrl+Shift+S',
            click: () => {
              this.mainWindow?.webContents.send('menu:save-project-as');
            }
          },
          { type: 'separator' },
          {
            label: 'Import Project',
            click: () => {
              this.mainWindow?.webContents.send('menu:import-project');
            }
          },
          {
            label: 'Export Project',
            accelerator: 'CmdOrCtrl+E',
            click: () => {
              this.mainWindow?.webContents.send('menu:export-project');
            }
          },
          { type: 'separator' },
          isMac ? { role: 'close' } : { role: 'quit' }
        ]
      },
      // Edit Menu
      {
        label: 'Edit',
        submenu: [
          {
            label: 'Undo',
            accelerator: 'CmdOrCtrl+Z',
            click: () => {
              this.mainWindow?.webContents.send('menu:undo');
            }
          },
          {
            label: 'Redo',
            accelerator: 'CmdOrCtrl+Shift+Z',
            click: () => {
              this.mainWindow?.webContents.send('menu:redo');
            }
          },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'delete' },
          { type: 'separator' },
          { role: 'selectAll' }
        ]
      },
      // View Menu
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      // Window Menu
      {
        label: 'Window',
        submenu: [
          { role: 'minimize' },
          { role: 'zoom' },
          ...(isMac ? [
            { type: 'separator' },
            { role: 'front' },
            { type: 'separator' },
            { role: 'window' }
          ] : [
            { role: 'close' }
          ])
        ]
      },
      // Help Menu
      {
        role: 'help',
        submenu: [
          {
            label: 'Learn More',
            click: async () => {
              const { shell } = require('electron');
              await shell.openExternal('https://github.com/robotic-arm-sequencer');
            }
          },
          {
            label: 'Documentation',
            click: async () => {
              const { shell } = require('electron');
              await shell.openExternal('https://github.com/robotic-arm-sequencer/docs');
            }
          },
          { type: 'separator' },
          {
            label: 'About',
            click: () => {
              dialog.showMessageBox({
                type: 'info',
                title: 'About Robotic Arm Sequencer',
                message: 'Robotic Arm Sequencer',
                detail: `Version: ${app.getVersion()}\n\nA Windows desktop application for programming and controlling 6-axis robotic arms with a cyberpunk-styled interface.`
              });
            }
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  private setupIPCHandlers(): void {
    // ==================== App Handlers ====================

    ipcMain.handle('app:getVersion', () => {
      return app.getVersion();
    });

    ipcMain.handle('app:getTheme', () => {
      return {
        shouldUseDarkColors: nativeTheme.shouldUseDarkColors,
        shouldUseHighContrastColors: nativeTheme.shouldUseHighContrastColors,
        shouldUseInvertedColorScheme: nativeTheme.shouldUseInvertedColorScheme
      };
    });

    ipcMain.handle('app:updateTrayStatus', (_, status: 'connected' | 'disconnected' | 'executing') => {
      this.updateTrayMenu(status);
    });

    // ==================== Project Operation Handlers ====================

    ipcMain.handle('project:create', async (_, project: Omit<ActionProject, 'id'>) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return await this.service.createProject(project);
      } catch (error) {
        console.error('project:create error:', error);
        throw error;
      }
    });

    ipcMain.handle('project:get', async (_, id: string) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return await this.service.getProject(id);
      } catch (error) {
        console.error('project:get error:', error);
        throw error;
      }
    });

    ipcMain.handle('project:getAll', async () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return await this.service.getAllProjects();
      } catch (error) {
        console.error('project:getAll error:', error);
        throw error;
      }
    });

    ipcMain.handle('project:update', async (_, project: ActionProject) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.updateProject(project);
      } catch (error) {
        console.error('project:update error:', error);
        throw error;
      }
    });

    ipcMain.handle('project:delete', async (_, id: string) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.deleteProject(id);
      } catch (error) {
        console.error('project:delete error:', error);
        throw error;
      }
    });

    // ==================== Frame Operation Handlers ====================

    ipcMain.handle('frame:add', async (_, projectId: string, frame: ActionFrame) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.addFrame(projectId, frame);
      } catch (error) {
        console.error('frame:add error:', error);
        throw error;
      }
    });

    ipcMain.handle('frame:insert', async (_, projectId: string, index: number, frame: ActionFrame) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.insertFrame(projectId, index, frame);
      } catch (error) {
        console.error('frame:insert error:', error);
        throw error;
      }
    });

    ipcMain.handle('frame:update', async (_, projectId: string, index: number, frame: ActionFrame) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.updateFrame(projectId, index, frame);
      } catch (error) {
        console.error('frame:update error:', error);
        throw error;
      }
    });

    ipcMain.handle('frame:delete', async (_, projectId: string, index: number) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.deleteFrame(projectId, index);
      } catch (error) {
        console.error('frame:delete error:', error);
        throw error;
      }
    });

    ipcMain.handle('frame:reorder', async (_, projectId: string, newOrder: number[]) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.reorderFrames(projectId, newOrder);
      } catch (error) {
        console.error('frame:reorder error:', error);
        throw error;
      }
    });

    // ==================== Undo/Redo Handlers ====================

    ipcMain.handle('edit:undo', async () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.undo();
      } catch (error) {
        console.error('edit:undo error:', error);
        throw error;
      }
    });

    ipcMain.handle('edit:redo', async () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.redo();
      } catch (error) {
        console.error('edit:redo error:', error);
        throw error;
      }
    });

    ipcMain.handle('edit:canUndo', () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return this.service.canUndo();
      } catch (error) {
        console.error('edit:canUndo error:', error);
        throw error;
      }
    });

    ipcMain.handle('edit:canRedo', () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return this.service.canRedo();
      } catch (error) {
        console.error('edit:canRedo error:', error);
        throw error;
      }
    });

    // ==================== Serial Communication Handlers ====================

    ipcMain.handle('serial:connect', async (_, portPath: string, baudRate: number) => {
      try {
        if (!this.serialPort) {
          throw new Error('Serial port manager not initialized');
        }
        await this.serialPort.connect(portPath, baudRate);
      } catch (error) {
        console.error('serial:connect error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:disconnect', async () => {
      try {
        if (!this.serialPort) {
          throw new Error('Serial port manager not initialized');
        }
        await this.serialPort.disconnect();
      } catch (error) {
        console.error('serial:disconnect error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:listPorts', async () => {
      try {
        if (!this.serialPort) {
          throw new Error('Serial port manager not initialized');
        }
        return await this.serialPort.listAvailablePorts();
      } catch (error) {
        console.error('serial:listPorts error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:isConnected', () => {
      try {
        if (!this.serialPort) {
          throw new Error('Serial port manager not initialized');
        }
        return this.serialPort.isPortConnected();
      } catch (error) {
        console.error('serial:isConnected error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:executeFrame', async (_, frame: ActionFrame) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.executeFrame(frame);
      } catch (error) {
        console.error('serial:executeFrame error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:executeSequence', async (_, frames: ActionFrame[], options: ExecutionOptions) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.executeSequence(frames, options);
      } catch (error) {
        console.error('serial:executeSequence error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:stopExecution', async () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.stopExecution();
      } catch (error) {
        console.error('serial:stopExecution error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:getExecutionState', () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return this.service.getExecutionState();
      } catch (error) {
        console.error('serial:getExecutionState error:', error);
        throw error;
      }
    });

    ipcMain.handle('serial:getCurrentProgress', () => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return this.service.getCurrentProgress();
      } catch (error) {
        console.error('serial:getCurrentProgress error:', error);
        throw error;
      }
    });

    // Send raw command (for CENTER, ARM, DISARM, etc.)
    ipcMain.handle('serial:sendRawCommand', async (_, command: string) => {
      try {
        if (!this.serialPort) {
          throw new Error('Serial port not initialized');
        }
        await this.serialPort.sendCommand(command);
      } catch (error) {
        console.error('serial:sendRawCommand error:', error);
        throw error;
      }
    });

    // ==================== Batch Download Handlers ====================

    ipcMain.handle('download:sequence', async (_, project: ActionProject, slotId: number, onProgress?: (progress: number) => void) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.downloadSequence(project, slotId, onProgress);
      } catch (error) {
        console.error('download:sequence error:', error);
        throw error;
      }
    });

    ipcMain.handle('download:formatSlot', async (_, slotId: number) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.formatSlot(slotId);
      } catch (error) {
        console.error('download:formatSlot error:', error);
        throw error;
      }
    });

    ipcMain.handle('download:setOfflineMode', async (_, slotId: number) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.setOfflineMode(slotId);
      } catch (error) {
        console.error('download:setOfflineMode error:', error);
        throw error;
      }
    });

    ipcMain.handle('download:readSequence', async (_, slotId: number) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        return await this.service.readSequence(slotId);
      } catch (error) {
        console.error('download:readSequence error:', error);
        throw error;
      }
    });

    // ==================== MP3 Command Handlers ====================

    ipcMain.handle('mp3:sendCommand', async (_, command: Mp3Command) => {
      try {
        if (!this.service) {
          throw new Error('Service not initialized');
        }
        await this.service.sendMp3Command(command);
      } catch (error) {
        console.error('mp3:sendCommand error:', error);
        throw error;
      }
    });

    // ==================== File Operation Handlers ====================

    ipcMain.handle('file:export', async (_, project: ActionProject) => {
      try {
        const result = await dialog.showSaveDialog({
          defaultPath: `${project.name}.armseq`,
          filters: [
            { name: 'Arm Sequence Files', extensions: ['armseq'] },
            { name: 'JSON Files', extensions: ['json'] }
          ],
          properties: ['createDirectory', 'showOverwriteConfirmation']
        });

        if (!result.canceled && result.filePath) {
          await fs.writeFile(result.filePath, JSON.stringify(project, null, 2), 'utf-8');
          return result.filePath;
        }
        return null;
      } catch (error) {
        console.error('file:export error:', error);
        throw error;
      }
    });

    ipcMain.handle('file:import', async (_, filePath: string) => {
      try {
        const fileContent = await fs.readFile(filePath, 'utf-8');
        const project: ActionProject = JSON.parse(fileContent);

        // Validate imported project structure
        if (!project.id || !project.name || !Array.isArray(project.frames)) {
          throw new Error('Invalid project file format');
        }

        return project;
      } catch (error) {
        console.error('file:import error:', error);
        throw error;
      }
    });

    ipcMain.handle('file:showSaveDialog', async (_, defaultName: string) => {
      try {
        const result = await dialog.showSaveDialog({
          defaultPath: defaultName,
          filters: [
            { name: 'Arm Sequence Files', extensions: ['armseq'] },
            { name: 'JSON Files', extensions: ['json'] }
          ],
          properties: ['createDirectory', 'showOverwriteConfirmation']
        });

        return result.canceled ? null : result.filePath;
      } catch (error) {
        console.error('file:showSaveDialog error:', error);
        throw error;
      }
    });

    ipcMain.handle('file:showOpenDialog', async () => {
      try {
        const result = await dialog.showOpenDialog({
          filters: [
            { name: 'Arm Sequence Files', extensions: ['armseq'] },
            { name: 'JSON Files', extensions: ['json'] }
          ],
          properties: ['openFile']
        });

        return result.canceled ? null : result.filePaths[0];
      } catch (error) {
        console.error('file:showOpenDialog error:', error);
        throw error;
      }
    });
  }
}

// Initialize the application
new MainApplication();