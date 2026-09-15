// Jest setup file for robotic-arm-sequencer tests
import '@testing-library/jest-dom';

// Mock Electron APIs for testing
const mockElectronAPI = {
  getVersion: jest.fn().mockResolvedValue('1.0.0'),
  createProject: jest.fn().mockResolvedValue('test-project-id'),
  getProject: jest.fn().mockResolvedValue(null),
  getAllProjects: jest.fn().mockResolvedValue([]),
  updateProject: jest.fn().mockResolvedValue(undefined),
  deleteProject: jest.fn().mockResolvedValue(undefined),
  connectSerial: jest.fn().mockResolvedValue(undefined),
  disconnectSerial: jest.fn().mockResolvedValue(undefined),
  listSerialPorts: jest.fn().mockResolvedValue([]),
  exportProject: jest.fn().mockResolvedValue('test-file-path'),
  importProject: jest.fn().mockResolvedValue({}),
  showSaveDialog: jest.fn().mockResolvedValue('test-save-path'),
  showOpenDialog: jest.fn().mockResolvedValue('test-open-path')
};

// Mock window.electronAPI for renderer tests
Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true
});

// Export for use in tests
export { mockElectronAPI };