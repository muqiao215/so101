import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import FrameList from '../renderer/components/timeline/FrameList';
import TimelineHeader from '../renderer/components/timeline/TimelineHeader';

describe('Timeline surface', () => {
  test('renders timeline summary cards and action labels in plain language', () => {
    const onAddFrame = jest.fn();

    render(
      <TimelineHeader
        totalFrames={3}
        totalDuration={2400}
        onAddFrame={onAddFrame}
      />
    );

    expect(screen.getByText('Frames')).toBeInTheDocument();
    expect(screen.getByText('Total duration')).toBeInTheDocument();
    expect(screen.getByText('Average frame time')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add frame' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Add frame' }));
    expect(onAddFrame).toHaveBeenCalledTimes(1);
  });

  test('shows a guided empty state when no frames exist', () => {
    render(
      <FrameList
        frames={[]}
        selectedFrameIndex={null}
        onFrameSelect={jest.fn()}
        onFrameEdit={jest.fn()}
        onFrameDelete={jest.fn()}
        onFrameDuplicate={jest.fn()}
        onFrameReorder={jest.fn()}
      />
    );

    expect(screen.getByText('No frames yet')).toBeInTheDocument();
    expect(
      screen.getByText('Add the first frame to start building this sequence.')
    ).toBeInTheDocument();
  });
});
