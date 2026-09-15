import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ipcClient } from '../renderer/ipc-client';
import ProjectListScreen from '../renderer/screens/ProjectListScreen';
import type { ActionProject } from '../shared/types';

jest.mock('../renderer/ipc-client', () => ({
  ipcClient: {
    getAllProjects: jest.fn(),
    createProject: jest.fn(),
    updateProject: jest.fn(),
    deleteProject: jest.fn(),
    exportProject: jest.fn(),
    importProject: jest.fn(),
    showOpenDialog: jest.fn(),
    listSerialPorts: jest.fn().mockResolvedValue([]),
    isSerialConnected: jest.fn().mockResolvedValue(false),
    connectSerial: jest.fn(),
    disconnectSerial: jest.fn(),
  },
}));

const mockIpcClient = ipcClient as jest.Mocked<typeof ipcClient>;

describe('ProjectListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockIpcClient.updateProject.mockResolvedValue(undefined);
    mockIpcClient.deleteProject.mockResolvedValue(undefined);
    mockIpcClient.exportProject.mockResolvedValue(null);
    mockIpcClient.importProject.mockResolvedValue(null);
    mockIpcClient.showOpenDialog.mockResolvedValue(null);
    mockIpcClient.connectSerial.mockResolvedValue(undefined);
    mockIpcClient.disconnectSerial.mockResolvedValue(undefined);
    mockIpcClient.listSerialPorts.mockResolvedValue([]);
    mockIpcClient.isSerialConnected.mockResolvedValue(false);
  });

  test('opens the newly created project after refreshing the project list', async () => {
    const onProjectOpen = jest.fn();
    const createdProject: ActionProject = {
      id: 'demo-1',
      name: 'Smoke Test Sequence',
      frames: [],
      createdAt: 111,
      modifiedAt: 111,
    };

    mockIpcClient.getAllProjects
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdProject]);
    mockIpcClient.createProject.mockResolvedValue(createdProject.id);

    render(<ProjectListScreen onProjectOpen={onProjectOpen} />);

    expect(await screen.findByText('NO PROJECTS YET')).toBeInTheDocument();

    fireEvent.click(screen.getByText('INITIALIZE PROJECT'));
    fireEvent.change(screen.getByPlaceholderText('Enter project name'), {
      target: { value: createdProject.name },
    });
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(mockIpcClient.createProject).toHaveBeenCalledWith({
        name: createdProject.name,
        frames: [],
        createdAt: expect.any(Number),
        modifiedAt: expect.any(Number),
      });
    });

    await waitFor(() => {
      expect(mockIpcClient.getAllProjects).toHaveBeenCalledTimes(2);
      expect(onProjectOpen).toHaveBeenCalledWith(createdProject);
    });
  });
});
