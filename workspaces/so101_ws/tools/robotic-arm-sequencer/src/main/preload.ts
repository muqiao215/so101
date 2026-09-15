import { contextBridge, ipcRenderer } from 'electron';
import type {
  ActionProject,
  ActionFrame,
  ExecutionOptions,
  ExecutionProgress,
  ExecutionState,
  Mp3Command,
  PortInfo
} from '../shared/types';

console.log('=== PRELOAD SCRIPT STARTED ===');
console.log('contextBridge available:', typeof contextBridge !== 'undefined');
console.log('ipcRenderer available:', typeof ipcRenderer !== 'undefined');

/**
 * Electron API exposed to renderer process via context bridge
 * Provides type-safe IPC communication between renderer and main process
 */
const electronAPI = {
  // ==================== App Methods ====================

  getVersion: (): Promise<string> =>
    ipcRenderer.invoke('app:getVersion'),

  getTheme: (): Promise<{ shouldUseDarkColors: boolean; shouldUseHighContrastColors: boolean; shouldUseInvertedColorScheme: boolean }> =>
    ipcRenderer.invoke('app:getTheme'),

  updateTrayStatus: (status: 'connected' | 'disconnected' | 'executing'): Promise<void> =>
    ipcRenderer.invoke('app:updateTrayStatus', status),

  // ==================== Event Listeners ====================

  on: {
    themeChanged: (callback: (theme: { shouldUseDarkColors: boolean; shouldUseHighContrastColors: boolean }) => void) => {
      ipcRenderer.on('theme:changed', (_, theme) => callback(theme));
    },

    fileOpened: (callback: (project: ActionProject) => void) => {
      ipcRenderer.on('file:opened', (_, project) => callback(project));
    },

    menuNewProject: (callback: () => void) => {
      ipcRenderer.on('menu:new-project', () => callback());
    },

    menuSaveProject: (callback: () => void) => {
      ipcRenderer.on('menu:save-project', () => callback());
    },

    menuSaveProjectAs: (callback: () => void) => {
      ipcRenderer.on('menu:save-project-as', () => callback());
    },

    menuImportProject: (callback: () => void) => {
      ipcRenderer.on('menu:import-project', () => callback());
    },

    menuExportProject: (callback: () => void) => {
      ipcRenderer.on('menu:export-project', () => callback());
    },

    menuUndo: (callback: () => void) => {
      ipcRenderer.on('menu:undo', () => callback());
    },

    menuRedo: (callback: () => void) => {
      ipcRenderer.on('menu:redo', () => callback());
    },
  },

  // ==================== Project Operations ====================

  project: {
    create: (project: Omit<ActionProject, 'id'>): Promise<string> =>
      ipcRenderer.invoke('project:create', project),

    get: (id: string): Promise<ActionProject | null> =>
      ipcRenderer.invoke('project:get', id),

    getAll: (): Promise<ActionProject[]> =>
      ipcRenderer.invoke('project:getAll'),

    update: (project: ActionProject): Promise<void> =>
      ipcRenderer.invoke('project:update', project),

    delete: (id: string): Promise<void> =>
      ipcRenderer.invoke('project:delete', id),
  },

  // ==================== Frame Operations ====================

  frame: {
    add: (projectId: string, frame: ActionFrame): Promise<void> =>
      ipcRenderer.invoke('frame:add', projectId, frame),

    insert: (projectId: string, index: number, frame: ActionFrame): Promise<void> =>
      ipcRenderer.invoke('frame:insert', projectId, index, frame),

    update: (projectId: string, index: number, frame: ActionFrame): Promise<void> =>
      ipcRenderer.invoke('frame:update', projectId, index, frame),

    delete: (projectId: string, index: number): Promise<void> =>
      ipcRenderer.invoke('frame:delete', projectId, index),

    reorder: (projectId: string, newOrder: number[]): Promise<void> =>
      ipcRenderer.invoke('frame:reorder', projectId, newOrder),
  },

  // ==================== Undo/Redo Operations ====================

  edit: {
    undo: (): Promise<void> =>
      ipcRenderer.invoke('edit:undo'),

    redo: (): Promise<void> =>
      ipcRenderer.invoke('edit:redo'),

    canUndo: (): Promise<boolean> =>
      ipcRenderer.invoke('edit:canUndo'),

    canRedo: (): Promise<boolean> =>
      ipcRenderer.invoke('edit:canRedo'),
  },

  // ==================== Serial Communication ====================

  serial: {
    connect: (portPath: string, baudRate: number): Promise<void> =>
      ipcRenderer.invoke('serial:connect', portPath, baudRate),

    disconnect: (): Promise<void> =>
      ipcRenderer.invoke('serial:disconnect'),

    listPorts: (): Promise<PortInfo[]> =>
      ipcRenderer.invoke('serial:listPorts'),

    isConnected: (): Promise<boolean> =>
      ipcRenderer.invoke('serial:isConnected'),

    executeFrame: (frame: ActionFrame): Promise<void> =>
      ipcRenderer.invoke('serial:executeFrame', frame),

    executeSequence: (frames: ActionFrame[], options: ExecutionOptions): Promise<void> =>
      ipcRenderer.invoke('serial:executeSequence', frames, options),

    stopExecution: (): Promise<void> =>
      ipcRenderer.invoke('serial:stopExecution'),

    getExecutionState: (): Promise<ExecutionState> =>
      ipcRenderer.invoke('serial:getExecutionState'),

    getCurrentProgress: (): Promise<ExecutionProgress | null> =>
      ipcRenderer.invoke('serial:getCurrentProgress'),

    sendRawCommand: (command: string): Promise<void> =>
      ipcRenderer.invoke('serial:sendRawCommand', command),
  },

  // ==================== Batch Download Operations ====================

  download: {
    sequence: (project: ActionProject, slotId: number, onProgress?: (progress: number) => void): Promise<void> =>
      ipcRenderer.invoke('download:sequence', project, slotId, onProgress),

    formatSlot: (slotId: number): Promise<void> =>
      ipcRenderer.invoke('download:formatSlot', slotId),

    setOfflineMode: (slotId: number): Promise<void> =>
      ipcRenderer.invoke('download:setOfflineMode', slotId),

    readSequence: (slotId: number): Promise<ActionFrame[]> =>
      ipcRenderer.invoke('download:readSequence', slotId),
  },

  // ==================== MP3 Commands ====================

  mp3: {
    sendCommand: (command: Mp3Command): Promise<void> =>
      ipcRenderer.invoke('mp3:sendCommand', command),
  },

  // ==================== File Operations ====================

  file: {
    export: (project: ActionProject): Promise<string | null> =>
      ipcRenderer.invoke('file:export', project),

    import: (filePath: string): Promise<ActionProject> =>
      ipcRenderer.invoke('file:import', filePath),

    showSaveDialog: (defaultName: string): Promise<string | null> =>
      ipcRenderer.invoke('file:showSaveDialog', defaultName),

    showOpenDialog: (): Promise<string | null> =>
      ipcRenderer.invoke('file:showOpenDialog'),
  },
};

// Expose the API to the renderer process
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Type definitions for the exposed API
export type ElectronAPI = typeof electronAPI;

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}