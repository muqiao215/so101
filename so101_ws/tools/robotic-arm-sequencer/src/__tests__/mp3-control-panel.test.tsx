/**
 * MP3ControlPanel Component Tests
 * 
 * Unit tests for MP3 control interface components
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MP3ControlPanel } from '../renderer/components/MP3ControlPanel';
import { MP3AssignmentModal } from '../renderer/components/MP3AssignmentModal';
import type { Mp3Command } from '../shared/types';

describe('MP3ControlPanel', () => {
  const mockOnCommand = jest.fn();
  const mockOnTrackSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders with default props', () => {
    render(
      <MP3ControlPanel
        onCommand={mockOnCommand}
      />
    );

    expect(screen.getByText(/MP3 CONTROL/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Play/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Stop/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Previous/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
  });

  test('sends play command with correct track ID', () => {
    render(
      <MP3ControlPanel
        currentTrackId={5}
        onCommand={mockOnCommand}
      />
    );

    const playButton = screen.getByRole('button', { name: /Play/i });
    fireEvent.click(playButton);

    expect(mockOnCommand).toHaveBeenCalledWith({
      type: 'play',
      trackId: 5
    });
  });

  test('sends stop command', () => {
    render(
      <MP3ControlPanel
        onCommand={mockOnCommand}
      />
    );

    // First play to enable stop
    const playButton = screen.getAllByText(/Play/i).find(el => el.tagName === 'SPAN' && el.parentElement?.tagName === 'BUTTON');
    fireEvent.click(playButton!.parentElement!);

    const stopButton = screen.getAllByText(/Stop/i).find(el => el.tagName === 'SPAN' && el.parentElement?.tagName === 'BUTTON');
    fireEvent.click(stopButton!.parentElement!);

    expect(mockOnCommand).toHaveBeenCalledWith({ type: 'stop' });
  });

  test('sends next command and updates track ID', () => {
    render(
      <MP3ControlPanel
        currentTrackId={10}
        onCommand={mockOnCommand}
        onTrackSelect={mockOnTrackSelect}
      />
    );

    const nextButton = screen.getByText(/Next/i);
    fireEvent.click(nextButton);

    expect(mockOnCommand).toHaveBeenCalledWith({ type: 'next' });
    expect(mockOnTrackSelect).toHaveBeenCalledWith(11);
  });

  test('sends previous command and updates track ID', () => {
    render(
      <MP3ControlPanel
        currentTrackId={10}
        onCommand={mockOnCommand}
        onTrackSelect={mockOnTrackSelect}
      />
    );

    const previousButton = screen.getByText(/Previous/i);
    fireEvent.click(previousButton);

    expect(mockOnCommand).toHaveBeenCalledWith({ type: 'previous' });
    expect(mockOnTrackSelect).toHaveBeenCalledWith(9);
  });

  test('sends volume command when slider changes', () => {
    render(
      <MP3ControlPanel
        currentVolume={15}
        onCommand={mockOnCommand}
      />
    );

    // Volume slider should be present - check for the label element specifically
    const volumeLabel = screen.getAllByText(/Volume/i).find(el => el.tagName === 'LABEL');
    expect(volumeLabel).toBeInTheDocument();
  });

  test('disables previous button at track 1', () => {
    render(
      <MP3ControlPanel
        currentTrackId={1}
        onCommand={mockOnCommand}
      />
    );

    const previousButton = screen.getAllByText(/Previous/i).find(el => el.tagName === 'SPAN' && el.parentElement?.tagName === 'BUTTON')?.parentElement;
    expect(previousButton).toBeDisabled();
  });

  test('disables next button at track 255', () => {
    render(
      <MP3ControlPanel
        currentTrackId={255}
        onCommand={mockOnCommand}
      />
    );

    const nextButton = screen.getAllByText(/Next/i).find(el => el.tagName === 'SPAN' && el.parentElement?.tagName === 'BUTTON')?.parentElement;
    expect(nextButton).toBeDisabled();
  });

  test('test audio button triggers play and auto-stop', async () => {
    jest.useFakeTimers();
    
    render(
      <MP3ControlPanel
        currentTrackId={5}
        onCommand={mockOnCommand}
      />
    );

    const testButton = screen.getByText(/Test Audio/i);
    fireEvent.click(testButton);

    expect(mockOnCommand).toHaveBeenCalledWith({
      type: 'play',
      trackId: 5
    });

    // Fast-forward time
    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(mockOnCommand).toHaveBeenCalledWith({ type: 'stop' });
    });

    jest.useRealTimers();
  });

  test('respects disabled prop', () => {
    render(
      <MP3ControlPanel
        onCommand={mockOnCommand}
        disabled={true}
      />
    );

    const playButton = screen.getAllByText(/Play/i).find(el => el.tagName === 'SPAN' && el.parentElement?.tagName === 'BUTTON')?.parentElement;
    expect(playButton).toBeDisabled();
  });

  test('allows track ID input between 1-255', () => {
    render(
      <MP3ControlPanel
        onCommand={mockOnCommand}
        onTrackSelect={mockOnTrackSelect}
        showTrackSelector={true}
      />
    );

    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '42' } });

    expect(mockOnTrackSelect).toHaveBeenCalledWith(42);
  });
});

describe('MP3AssignmentModal', () => {
  const mockOnClose = jest.fn();
  const mockOnAssign = jest.fn();
  const mockOnTestCommand = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders when open', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    expect(screen.getByText(/Assign MP3 Track/i)).toBeInTheDocument();
  });

  test('does not render when closed', () => {
    render(
      <MP3AssignmentModal
        isOpen={false}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    expect(screen.queryByText(/Assign MP3 Track/i)).not.toBeInTheDocument();
  });

  test('calls onAssign with selected track ID', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        currentSoundId={5}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    const assignButton = screen.getByText(/Assign Track/i);
    fireEvent.click(assignButton);

    expect(mockOnAssign).toHaveBeenCalledWith(5);
    expect(mockOnClose).toHaveBeenCalled();
  });

  test('calls onAssign with undefined when removing sound', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        currentSoundId={5}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    const removeButton = screen.getByText(/Remove Sound/i);
    fireEvent.click(removeButton);

    expect(mockOnAssign).toHaveBeenCalledWith(undefined);
    expect(mockOnClose).toHaveBeenCalled();
  });

  test('closes on cancel button', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    const cancelButton = screen.getByText(/Cancel/i);
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
    expect(mockOnAssign).not.toHaveBeenCalled();
  });

  test('shows current assignment info when soundId is provided', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        currentSoundId={42}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    expect(screen.getByText(/Current Assignment:/i)).toBeInTheDocument();
    expect(screen.getByText(/Track 042/i)).toBeInTheDocument();
  });

  test('does not show remove button when no current sound', () => {
    render(
      <MP3AssignmentModal
        isOpen={true}
        onClose={mockOnClose}
        onAssign={mockOnAssign}
        onTestCommand={mockOnTestCommand}
      />
    );

    expect(screen.queryByText(/Remove Sound/i)).not.toBeInTheDocument();
  });
});
