/**
 * RealTimeControlScreen Component Tests
 * 
 * Basic rendering and functionality tests for the real-time control interface
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import RealTimeControlScreen from '../renderer/screens/RealTimeControlScreen';
import type { ActionProject, ActionFrame } from '../shared/types';

// Mock window.electronAPI
const mockElectronAPI = {
  getVersion: jest.fn().mockResolvedValue('1.0.0'),
  project: {
    create: jest.fn(),
    get: jest.fn(),
    getAll: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
  },
  frame: {
    add: jest.fn(),
    insert: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    reorder: jest.fn(),
  },
  edit: {
    undo: jest.fn(),
    redo: jest.fn(),
    canUndo: jest.fn(),
    canRedo: jest.fn(),
  },
  serial: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    listPorts: jest.fn().mockResolvedValue([]),
    isConnected: jest.fn().mockResolvedValue(false),
    executeFrame: jest.fn(),
    executeSequence: jest.fn(),
    stopExecution: jest.fn(),
    getExecutionState: jest.fn(),
    getCurrentProgress: jest.fn(),
  },
  download: {
    sequence: jest.fn(),
    formatSlot: jest.fn(),
    setOfflineMode: jest.fn(),
    readSequence: jest.fn(),
  },
  mp3: {
    sendCommand: jest.fn(),
  },
  file: {
    export: jest.fn(),
    import: jest.fn(),
    showSaveDialog: jest.fn(),
    showOpenDialog: jest.fn(),
  },
};

// @ts-ignore
global.window.electronAPI = mockElectronAPI;

describe('RealTimeControlScreen Component Tests', () => {
  const mockProject: ActionProject = {
    id: 'test-project-1',
    name: 'Test Project',
    frames: [],
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should render the component with all main sections', () => {
    render(<RealTimeControlScreen />);
    
    // Check for main title
    expect(screen.getByText('REAL-TIME CONTROL')).toBeInTheDocument();
    
    // Check for servo controls section
    expect(screen.getByText('SERVO CONTROLS')).toBeInTheDocument();
    
    // Check for visualization section
    expect(screen.getByText('ARM VISUALIZATION')).toBeInTheDocument();
    
    // Check for status section
    expect(screen.getByText('SYSTEM STATUS')).toBeInTheDocument();
    
    // Check for frame capture section
    expect(screen.getByText('FRAME CAPTURE')).toBeInTheDocument();
    
    // Check for safety controls section
    expect(screen.getByText('SAFETY CONTROLS')).toBeInTheDocument();
  });

  test('should render 6 servo sliders', () => {
    render(<RealTimeControlScreen />);
    
    // Check for all 6 axis labels
    for (let i = 1; i <= 6; i++) {
      expect(screen.getByText(`AXIS ${i}`)).toBeInTheDocument();
    }
  });

  test('should render emergency stop button', () => {
    render(<RealTimeControlScreen />);
    
    expect(screen.getByText('EMERGENCY STOP')).toBeInTheDocument();
  });

  test('should render frame capture button', () => {
    render(<RealTimeControlScreen />);
    
    expect(screen.getByText('📸 CAPTURE FRAME')).toBeInTheDocument();
  });

  test('should call onFrameCapture when capture button is clicked', () => {
    const mockOnFrameCapture = jest.fn();
    mockElectronAPI.serial.listPorts.mockResolvedValue([{ path: 'COM3' }]);
    
    render(
      <RealTimeControlScreen
        project={mockProject}
        onFrameCapture={mockOnFrameCapture}
      />
    );
    
    // Wait for connection check
    setTimeout(() => {
      const captureButton = screen.getByText('📸 CAPTURE FRAME');
      fireEvent.click(captureButton);
      
      expect(mockOnFrameCapture).toHaveBeenCalledTimes(1);
      expect(mockOnFrameCapture).toHaveBeenCalledWith(
        expect.objectContaining({
          sequenceId: 0,
          duration: 1000,
          servos: expect.any(Object),
        })
      );
    }, 100);
  });

  test('should call onBack when back button is clicked', () => {
    const mockOnBack = jest.fn();
    
    render(<RealTimeControlScreen onBack={mockOnBack} />);
    
    const backButton = screen.getByText('BACK');
    fireEvent.click(backButton);
    
    expect(mockOnBack).toHaveBeenCalledTimes(1);
  });

  test('should display project name when provided', () => {
    render(<RealTimeControlScreen project={mockProject} />);
    
    expect(screen.getByText('[Test Project]')).toBeInTheDocument();
  });

  test('should render reset button for servo controls', () => {
    render(<RealTimeControlScreen />);
    
    expect(screen.getByText('RESET')).toBeInTheDocument();
  });

  test('should show all servo positions in the position readout', () => {
    render(<RealTimeControlScreen />);
    
    // Check for position readout labels
    for (let i = 1; i <= 6; i++) {
      expect(screen.getByText(`AXIS ${i}:`)).toBeInTheDocument();
    }
  });

  test('should render status monitor with connection status', () => {
    render(<RealTimeControlScreen />);
    
    expect(screen.getByText('CONNECTION')).toBeInTheDocument();
    expect(screen.getByText('VOLTAGE')).toBeInTheDocument();
    expect(screen.getByText('COMM STATE')).toBeInTheDocument();
  });
});
