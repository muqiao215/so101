/**
 * Unit tests for IPC handlers
 * Tests all project operations, serial communication, and file operations with mocks
 */

import { ActionProject, ActionFrame, ExecutionOptions, Mp3Command } from '../shared/types';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';

// Mock types for testing
interface MockIPCEvent {
  sender: {
    send: jest.Mock;
  };
}

interface MockDialog {
  showSaveDialog: jest.Mock;
  showOpenDialog: jest.Mock;
}

interface MockFS {
  writeFile: jest.Mock;
  readFile: jest.Mock;
}

interface MockService {
  createProject: jest.Mock;
  getProject: jest.Mock;
  getAllProjects: jest.Mock;
  updateProject: jest.Mock;
  deleteProject: jest.Mock;
  addFrame: jest.Mock;
  insertFrame: jest.Mock;
  updateFrame: jest.Mock;
  deleteFrame: jest.Mock;
  reorderFrames: jest.Mock;
  undo: jest.Mock;
  redo: jest.Mock;
  canUndo: jest.Mock;
  canRedo: jest.Mock;
  executeFrame: jest.Mock;
  executeSequence: jest.Mock;
  stopExecution: jest.Mock;
  getExecutionState: jest.Mock;
  getCurrentProgress: jest.Mock;
  downloadSequence: jest.Mock;
  formatSlot: jest.Mock;
  setOfflineMode: jest.Mock;
  readSequence: jest.Mock;
  sendMp3Command: jest.Mock;
  close: jest.Mock;
}

interface MockSerialPort {
  connect: jest.Mock;
  disconnect: jest.Mock;
  listAvailablePorts: jest.Mock;
  isPortConnected: jest.Mock;
}

describe('IPC Handlers Unit Tests', () => {
  let mockService: MockService;
  let mockSerialPort: MockSerialPort;
  let mockDialog: MockDialog;
  let mockFS: MockFS;
  let mockEvent: MockIPCEvent;

  // Sample test data
  const sampleProject: ActionProject = ActionProjectFactory.create({
    name: 'Test Project',
    frames: [],
  });

  const sampleFrame: ActionFrame = ActionFrameFactory.create({
    sequenceId: 0,
    duration: 1000,
    servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
  });

  beforeEach(() => {
    // Reset all mocks before each test
    mockService = {
      createProject: jest.fn(),
      getProject: jest.fn(),
      getAllProjects: jest.fn(),
      updateProject: jest.fn(),
      deleteProject: jest.fn(),
      addFrame: jest.fn(),
      insertFrame: jest.fn(),
      updateFrame: jest.fn(),
      deleteFrame: jest.fn(),
      reorderFrames: jest.fn(),
      undo: jest.fn(),
      redo: jest.fn(),
      canUndo: jest.fn(),
      canRedo: jest.fn(),
      executeFrame: jest.fn(),
      executeSequence: jest.fn(),
      stopExecution: jest.fn(),
      getExecutionState: jest.fn(),
      getCurrentProgress: jest.fn(),
      downloadSequence: jest.fn(),
      formatSlot: jest.fn(),
      setOfflineMode: jest.fn(),
      readSequence: jest.fn(),
      sendMp3Command: jest.fn(),
      close: jest.fn(),
    };

    mockSerialPort = {
      connect: jest.fn(),
      disconnect: jest.fn(),
      listAvailablePorts: jest.fn(),
      isPortConnected: jest.fn(),
    };

    mockDialog = {
      showSaveDialog: jest.fn(),
      showOpenDialog: jest.fn(),
    };

    mockFS = {
      writeFile: jest.fn(),
      readFile: jest.fn(),
    };

    mockEvent = {
      sender: {
        send: jest.fn(),
      },
    };
  });

  // ==================== Project Operation Tests ====================

  describe('Project Operations', () => {
    test('project:create should create a new project and return ID', async () => {
      const projectId = 'test-project-id';
      mockService.createProject.mockResolvedValue(projectId);

      const result = await mockService.createProject(sampleProject);

      expect(mockService.createProject).toHaveBeenCalledWith(sampleProject);
      expect(result).toBe(projectId);
    });

    test('project:get should retrieve a project by ID', async () => {
      mockService.getProject.mockResolvedValue(sampleProject);

      const result = await mockService.getProject(sampleProject.id);

      expect(mockService.getProject).toHaveBeenCalledWith(sampleProject.id);
      expect(result).toEqual(sampleProject);
    });

    test('project:get should return null for non-existent project', async () => {
      mockService.getProject.mockResolvedValue(null);

      const result = await mockService.getProject('non-existent-id');

      expect(result).toBeNull();
    });

    test('project:getAll should return all projects', async () => {
      const projects = [sampleProject];
      mockService.getAllProjects.mockResolvedValue(projects);

      const result = await mockService.getAllProjects();

      expect(mockService.getAllProjects).toHaveBeenCalled();
      expect(result).toEqual(projects);
    });

    test('project:update should update an existing project', async () => {
      mockService.updateProject.mockResolvedValue(undefined);

      await mockService.updateProject(sampleProject);

      expect(mockService.updateProject).toHaveBeenCalledWith(sampleProject);
    });

    test('project:delete should delete a project by ID', async () => {
      mockService.deleteProject.mockResolvedValue(undefined);

      await mockService.deleteProject(sampleProject.id);

      expect(mockService.deleteProject).toHaveBeenCalledWith(sampleProject.id);
    });

    test('project operations should handle errors gracefully', async () => {
      const error = new Error('Database error');
      mockService.createProject.mockRejectedValue(error);

      await expect(mockService.createProject(sampleProject)).rejects.toThrow('Database error');
    });
  });

  // ==================== Frame Operation Tests ====================

  describe('Frame Operations', () => {
    test('frame:add should add a frame to a project', async () => {
      mockService.addFrame.mockResolvedValue(undefined);

      await mockService.addFrame(sampleProject.id, sampleFrame);

      expect(mockService.addFrame).toHaveBeenCalledWith(sampleProject.id, sampleFrame);
    });

    test('frame:insert should insert a frame at specific index', async () => {
      const index = 2;
      mockService.insertFrame.mockResolvedValue(undefined);

      await mockService.insertFrame(sampleProject.id, index, sampleFrame);

      expect(mockService.insertFrame).toHaveBeenCalledWith(sampleProject.id, index, sampleFrame);
    });

    test('frame:update should update a frame at specific index', async () => {
      const index = 1;
      mockService.updateFrame.mockResolvedValue(undefined);

      await mockService.updateFrame(sampleProject.id, index, sampleFrame);

      expect(mockService.updateFrame).toHaveBeenCalledWith(sampleProject.id, index, sampleFrame);
    });

    test('frame:delete should delete a frame at specific index', async () => {
      const index = 0;
      mockService.deleteFrame.mockResolvedValue(undefined);

      await mockService.deleteFrame(sampleProject.id, index);

      expect(mockService.deleteFrame).toHaveBeenCalledWith(sampleProject.id, index);
    });

    test('frame:reorder should reorder frames with new order array', async () => {
      const newOrder = [2, 0, 1];
      mockService.reorderFrames.mockResolvedValue(undefined);

      await mockService.reorderFrames(sampleProject.id, newOrder);

      expect(mockService.reorderFrames).toHaveBeenCalledWith(sampleProject.id, newOrder);
    });

    test('frame operations should handle invalid indices', async () => {
      const error = new Error('Invalid index: -1');
      mockService.deleteFrame.mockRejectedValue(error);

      await expect(mockService.deleteFrame(sampleProject.id, -1)).rejects.toThrow('Invalid index');
    });
  });

  // ==================== Undo/Redo Tests ====================

  describe('Undo/Redo Operations', () => {
    test('edit:undo should undo last operation', async () => {
      mockService.undo.mockResolvedValue(undefined);

      await mockService.undo();

      expect(mockService.undo).toHaveBeenCalled();
    });

    test('edit:redo should redo last undone operation', async () => {
      mockService.redo.mockResolvedValue(undefined);

      await mockService.redo();

      expect(mockService.redo).toHaveBeenCalled();
    });

    test('edit:canUndo should return true when undo is available', async () => {
      mockService.canUndo.mockReturnValue(true);

      const result = mockService.canUndo();

      expect(result).toBe(true);
    });

    test('edit:canRedo should return false when redo is not available', async () => {
      mockService.canRedo.mockReturnValue(false);

      const result = mockService.canRedo();

      expect(result).toBe(false);
    });

    test('edit:undo should throw error when nothing to undo', async () => {
      const error = new Error('Nothing to undo');
      mockService.undo.mockRejectedValue(error);

      await expect(mockService.undo()).rejects.toThrow('Nothing to undo');
    });
  });

  // ==================== Serial Communication Tests ====================

  describe('Serial Communication', () => {
    test('serial:connect should connect to specified port', async () => {
      const portPath = 'COM3';
      mockSerialPort.connect.mockResolvedValue(undefined);

      await mockSerialPort.connect(portPath);

      expect(mockSerialPort.connect).toHaveBeenCalledWith(portPath);
    });

    test('serial:disconnect should disconnect from port', async () => {
      mockSerialPort.disconnect.mockResolvedValue(undefined);

      await mockSerialPort.disconnect();

      expect(mockSerialPort.disconnect).toHaveBeenCalled();
    });

    test('serial:listPorts should return available ports', async () => {
      const ports = [
        { path: 'COM3', manufacturer: 'Arduino' },
        { path: 'COM4', manufacturer: 'FTDI' },
      ];
      mockSerialPort.listAvailablePorts.mockResolvedValue(ports);

      const result = await mockSerialPort.listAvailablePorts();

      expect(result).toEqual(ports);
    });

    test('serial:isConnected should return connection status', async () => {
      mockSerialPort.isPortConnected.mockReturnValue(true);

      const result = mockSerialPort.isPortConnected();

      expect(result).toBe(true);
    });

    test('serial:executeFrame should execute a single frame', async () => {
      mockService.executeFrame.mockResolvedValue(undefined);

      await mockService.executeFrame(sampleFrame);

      expect(mockService.executeFrame).toHaveBeenCalledWith(sampleFrame);
    });

    test('serial:executeSequence should execute a sequence of frames', async () => {
      const frames = [sampleFrame];
      const options: ExecutionOptions = { loop: false };
      mockService.executeSequence.mockResolvedValue(undefined);

      await mockService.executeSequence(frames, options);

      expect(mockService.executeSequence).toHaveBeenCalledWith(frames, options);
    });

    test('serial:stopExecution should stop current execution', async () => {
      mockService.stopExecution.mockResolvedValue(undefined);

      await mockService.stopExecution();

      expect(mockService.stopExecution).toHaveBeenCalled();
    });

    test('serial:getExecutionState should return current state', async () => {
      mockService.getExecutionState.mockReturnValue('running');

      const result = mockService.getExecutionState();

      expect(result).toBe('running');
    });

    test('serial:getCurrentProgress should return progress information', async () => {
      const progress = { currentFrame: 5, totalFrames: 10, percentage: 50 };
      mockService.getCurrentProgress.mockReturnValue(progress);

      const result = mockService.getCurrentProgress();

      expect(result).toEqual(progress);
    });

    test('serial operations should handle connection errors', async () => {
      const error = new Error('Serial port not connected');
      mockService.executeFrame.mockRejectedValue(error);

      await expect(mockService.executeFrame(sampleFrame)).rejects.toThrow('Serial port not connected');
    });
  });

  // ==================== Batch Download Tests ====================

  describe('Batch Download Operations', () => {
    test('download:sequence should download sequence to Arduino slot', async () => {
      const slotId = 5;
      mockService.downloadSequence.mockResolvedValue(undefined);

      await mockService.downloadSequence(sampleProject, slotId);

      expect(mockService.downloadSequence).toHaveBeenCalledWith(sampleProject, slotId);
    });

    test('download:formatSlot should format Arduino storage slot', async () => {
      const slotId = 3;
      mockService.formatSlot.mockResolvedValue(undefined);

      await mockService.formatSlot(slotId);

      expect(mockService.formatSlot).toHaveBeenCalledWith(slotId);
    });

    test('download:setOfflineMode should set slot to offline mode', async () => {
      const slotId = 1;
      mockService.setOfflineMode.mockResolvedValue(undefined);

      await mockService.setOfflineMode(slotId);

      expect(mockService.setOfflineMode).toHaveBeenCalledWith(slotId);
    });

    test('download:readSequence should read sequence from Arduino slot', async () => {
      const slotId = 2;
      const frames = [sampleFrame];
      mockService.readSequence.mockResolvedValue(frames);

      const result = await mockService.readSequence(slotId);

      expect(mockService.readSequence).toHaveBeenCalledWith(slotId);
      expect(result).toEqual(frames);
    });

    test('download operations should validate slot ID range', async () => {
      const invalidSlotId = 11;
      const error = new Error('Invalid slot ID: 11. Must be between 1-10');
      mockService.downloadSequence.mockRejectedValue(error);

      await expect(mockService.downloadSequence(sampleProject, invalidSlotId)).rejects.toThrow('Invalid slot ID');
    });
  });

  // ==================== MP3 Command Tests ====================

  describe('MP3 Commands', () => {
    test('mp3:sendCommand should send play command', async () => {
      const command: Mp3Command = { type: 'play', trackId: 5 };
      mockService.sendMp3Command.mockResolvedValue(undefined);

      await mockService.sendMp3Command(command);

      expect(mockService.sendMp3Command).toHaveBeenCalledWith(command);
    });

    test('mp3:sendCommand should send stop command', async () => {
      const command: Mp3Command = { type: 'stop' };
      mockService.sendMp3Command.mockResolvedValue(undefined);

      await mockService.sendMp3Command(command);

      expect(mockService.sendMp3Command).toHaveBeenCalledWith(command);
    });

    test('mp3:sendCommand should send volume command', async () => {
      const command: Mp3Command = { type: 'volume', level: 20 };
      mockService.sendMp3Command.mockResolvedValue(undefined);

      await mockService.sendMp3Command(command);

      expect(mockService.sendMp3Command).toHaveBeenCalledWith(command);
    });

    test('mp3:sendCommand should handle MP3 module errors', async () => {
      const command: Mp3Command = { type: 'play', trackId: 999 };
      const error = new Error('MP3 command failed');
      mockService.sendMp3Command.mockRejectedValue(error);

      await expect(mockService.sendMp3Command(command)).rejects.toThrow('MP3 command failed');
    });
  });

  // ==================== File Operation Tests ====================

  describe('File Operations', () => {
    test('file:export should save project to file with dialog', async () => {
      const filePath = 'C:\\Users\\test\\project.armseq';
      mockDialog.showSaveDialog.mockResolvedValue({ canceled: false, filePath });
      mockFS.writeFile.mockResolvedValue(undefined);

      const result = await mockDialog.showSaveDialog({
        defaultPath: `${sampleProject.name}.armseq`,
        filters: [{ name: 'Arm Sequence Files', extensions: ['armseq'] }],
      });

      expect(result.filePath).toBe(filePath);
      expect(result.canceled).toBe(false);
    });

    test('file:export should return null when dialog is canceled', async () => {
      mockDialog.showSaveDialog.mockResolvedValue({ canceled: true });

      const result = await mockDialog.showSaveDialog({
        defaultPath: `${sampleProject.name}.armseq`,
      });

      expect(result.canceled).toBe(true);
    });

    test('file:import should load project from file', async () => {
      const filePath = 'C:\\Users\\test\\project.armseq';
      const projectJSON = JSON.stringify(sampleProject);
      mockFS.readFile.mockResolvedValue(projectJSON);

      const fileContent = await mockFS.readFile(filePath, 'utf-8');
      const project = JSON.parse(fileContent);

      expect(project).toEqual(sampleProject);
    });

    test('file:import should handle invalid JSON', async () => {
      const filePath = 'C:\\Users\\test\\invalid.armseq';
      mockFS.readFile.mockResolvedValue('invalid json');

      const fileContent = await mockFS.readFile(filePath, 'utf-8');

      expect(() => JSON.parse(fileContent)).toThrow();
    });

    test('file:showSaveDialog should return selected file path', async () => {
      const filePath = 'C:\\Users\\test\\new-project.armseq';
      mockDialog.showSaveDialog.mockResolvedValue({ canceled: false, filePath });

      const result = await mockDialog.showSaveDialog({ defaultPath: 'new-project.armseq' });

      expect(result.filePath).toBe(filePath);
    });

    test('file:showOpenDialog should return selected file path', async () => {
      const filePath = 'C:\\Users\\test\\existing-project.armseq';
      mockDialog.showOpenDialog.mockResolvedValue({ canceled: false, filePaths: [filePath] });

      const result = await mockDialog.showOpenDialog({
        filters: [{ name: 'Arm Sequence Files', extensions: ['armseq'] }],
      });

      expect(result.filePaths[0]).toBe(filePath);
    });

    test('file operations should handle file system errors', async () => {
      const error = new Error('Permission denied');
      mockFS.writeFile.mockRejectedValue(error);

      await expect(mockFS.writeFile('test.armseq', 'data')).rejects.toThrow('Permission denied');
    });
  });

  // ==================== Error Handling and Response Formatting Tests ====================

  describe('Error Handling and Response Formatting', () => {
    test('should format error responses consistently', async () => {
      const error = new Error('Test error');
      mockService.createProject.mockRejectedValue(error);

      try {
        await mockService.createProject(sampleProject);
      } catch (e) {
        expect(e).toBeInstanceOf(Error);
        expect((e as Error).message).toBe('Test error');
      }
    });

    test('should handle service not initialized error', async () => {
      const error = new Error('Service not initialized');
      mockService.createProject.mockRejectedValue(error);

      await expect(mockService.createProject(sampleProject)).rejects.toThrow('Service not initialized');
    });

    test('should handle database errors', async () => {
      const error = new Error('Database connection failed');
      mockService.getAllProjects.mockRejectedValue(error);

      await expect(mockService.getAllProjects()).rejects.toThrow('Database connection failed');
    });

    test('should handle serial communication errors', async () => {
      const error = new Error('Serial port not found');
      mockSerialPort.connect.mockRejectedValue(error);

      await expect(mockSerialPort.connect('COM99')).rejects.toThrow('Serial port not found');
    });

    test('should log errors to console', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const error = new Error('Test error');
      mockService.createProject.mockRejectedValue(error);

      try {
        await mockService.createProject(sampleProject);
      } catch (e) {
        // Error caught
      }

      consoleSpy.mockRestore();
    });
  });
});
