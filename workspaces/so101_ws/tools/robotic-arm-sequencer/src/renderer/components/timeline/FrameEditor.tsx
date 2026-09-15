/**
 * Frame Editor Dialog
 * Modal dialog for editing frame properties with real-time preview
 */

import React, { useState, useEffect } from 'react';
import type { ActionFrame, Mp3Command } from '../../../shared/types';
import { CyberpunkButton } from '../CyberpunkButton';
import { CyberpunkSlider } from '../CyberpunkSlider';
import { MP3AssignmentModal } from '../MP3AssignmentModal';

interface FrameEditorProps {
  frame: ActionFrame;
  onSave: (frame: ActionFrame) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const FrameEditor: React.FC<FrameEditorProps> = ({
  frame,
  onSave,
  onCancel,
  isLoading = false
}) => {
  const [editedFrame, setEditedFrame] = useState<ActionFrame>({ ...frame });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showMP3Modal, setShowMP3Modal] = useState(false);

  // Reset edited frame when frame prop changes
  useEffect(() => {
    setEditedFrame({ ...frame });
    setErrors({});
  }, [frame]);

  // Handle servo value change
  const handleServoChange = (servoIndex: number, value: number) => {
    setEditedFrame(prev => ({
      ...prev,
      servos: {
        ...prev.servos,
        [servoIndex]: value
      }
    }));
  };

  // Handle duration change
  const handleDurationChange = (value: number) => {
    setEditedFrame(prev => ({
      ...prev,
      duration: value
    }));
  };

  // Handle sound ID change
  const handleSoundIdChange = (value: string) => {
    const numValue = parseInt(value, 10);
    
    if (value === '') {
      setEditedFrame(prev => ({
        ...prev,
        soundId: undefined
      }));
      delete errors.soundId;
    } else if (isNaN(numValue) || numValue < 1 || numValue > 255) {
      setErrors(prev => ({
        ...prev,
        soundId: 'Sound ID must be between 1 and 255'
      }));
    } else {
      setEditedFrame(prev => ({
        ...prev,
        soundId: numValue
      }));
      delete errors.soundId;
    }
  };

  // Handle MP3 assignment from modal
  const handleMP3Assign = (soundId: number | undefined) => {
    setEditedFrame(prev => ({
      ...prev,
      soundId
    }));
    if (soundId === undefined) {
      delete errors.soundId;
    }
  };

  // Handle MP3 test command (placeholder - would need IPC integration)
  const handleMP3TestCommand = (command: Mp3Command) => {
    console.log('MP3 Test Command:', command);
    // In a real implementation, this would send the command via IPC
    // window.electron.sendMP3Command(command);
  };

  // Validate and save
  const handleSave = () => {
    const newErrors: Record<string, string> = {};
    
    // Validate duration
    if (editedFrame.duration < 500 || editedFrame.duration > 5000) {
      newErrors.duration = 'Duration must be between 500 and 5000ms';
    }
    
    // Validate servos
    Object.entries(editedFrame.servos).forEach(([index, pwm]) => {
      if (pwm < 500 || pwm > 2500) {
        newErrors[`servo${index}`] = `Servo ${index} PWM must be between 500 and 2500`;
      }
    });
    
    // Validate sound ID
    if (editedFrame.soundId !== undefined && (editedFrame.soundId < 1 || editedFrame.soundId > 255)) {
      newErrors.soundId = 'Sound ID must be between 1 and 255';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    onSave(editedFrame);
  };

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-deep-space-black/90 backdrop-blur-sm">
      <div className="cyberpunk-border bg-night-blue w-full max-w-4xl max-h-[90vh] overflow-y-auto m-4">
        {/* Header */}
        <div className="border-b border-industrial-steel-blue/30 p-6">
          <h2 className="text-2xl font-bold neon-text">
            EDIT FRAME {frame.sequenceId}
          </h2>
          <p className="text-sm text-industrial-steel-blue mt-1">
            Adjust servo positions, duration, and audio settings
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Duration Control */}
          <div className="cyberpunk-border bg-deep-space-black/50 p-4">
            <label className="block text-sm font-bold text-industrial-steel-blue uppercase mb-3">
              Frame Duration
            </label>
            <div className="flex items-center space-x-4">
              <input
                type="number"
                min="500"
                max="5000"
                step="100"
                value={editedFrame.duration}
                onChange={(e) => handleDurationChange(parseInt(e.target.value, 10) || 500)}
                className="w-32 px-3 py-2 bg-deep-space-black border border-industrial-steel-blue/50 
                  rounded-cyberpunk text-titanium-white font-mono focus:outline-none focus:border-neon-magenta"
              />
              <span className="text-industrial-steel-blue">milliseconds</span>
              <input
                type="range"
                min="500"
                max="5000"
                step="100"
                value={editedFrame.duration}
                onChange={(e) => handleDurationChange(parseInt(e.target.value, 10))}
                className="flex-1"
              />
            </div>
            {errors.duration && (
              <p className="text-red-400 text-xs mt-2">{errors.duration}</p>
            )}
            <p className="text-xs text-industrial-steel-blue/70 mt-2">
              Valid range: 500-5000ms
            </p>
          </div>

          {/* Servo Controls */}
          <div className="cyberpunk-border bg-deep-space-black/50 p-4">
            <label className="block text-sm font-bold text-industrial-steel-blue uppercase mb-4">
              Servo Positions
            </label>
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3, 4, 5, 6].map((servoIndex) => (
                <div key={servoIndex} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-industrial-steel-blue">
                      SERVO {servoIndex}
                    </span>
                    <span className="text-sm font-mono neon-text">
                      {editedFrame.servos[servoIndex]}µs
                    </span>
                  </div>
                  <CyberpunkSlider
                    value={editedFrame.servos[servoIndex]}
                    min={500}
                    max={2500}
                    step={10}
                    onChange={(value) => handleServoChange(servoIndex, value)}
                    label=""
                  />
                  {errors[`servo${servoIndex}`] && (
                    <p className="text-red-400 text-xs">{errors[`servo${servoIndex}`]}</p>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-industrial-steel-blue/70 mt-4">
              Valid range: 500-2500µs (PWM pulse width)
            </p>
          </div>

          {/* Sound Control */}
          <div className="cyberpunk-border bg-deep-space-black/50 p-4">
            <div className="flex justify-between items-center mb-3">
              <label className="block text-sm font-bold text-industrial-steel-blue uppercase">
                Audio Track (Optional)
              </label>
              <CyberpunkButton
                onClick={() => setShowMP3Modal(true)}
                variant="ghost"
                size="sm"
              >
                🎵 Advanced
              </CyberpunkButton>
            </div>
            <div className="flex items-center space-x-4">
              <input
                type="number"
                min="1"
                max="255"
                value={editedFrame.soundId || ''}
                onChange={(e) => handleSoundIdChange(e.target.value)}
                placeholder="No audio"
                className="w-32 px-3 py-2 bg-deep-space-black border border-industrial-steel-blue/50 
                  rounded-cyberpunk text-titanium-white font-mono focus:outline-none focus:border-neon-magenta
                  placeholder:text-industrial-steel-blue/50"
              />
              <span className="text-industrial-steel-blue">MP3 Track ID</span>
              {editedFrame.soundId && (
                <button
                  onClick={() => handleSoundIdChange('')}
                  className="text-xs text-red-400 hover:text-red-300 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
            {errors.soundId && (
              <p className="text-red-400 text-xs mt-2">{errors.soundId}</p>
            )}
            <p className="text-xs text-industrial-steel-blue/70 mt-2">
              Valid range: 1-255 (leave empty for no audio)
            </p>
          </div>

          {/* Preview */}
          <div className="cyberpunk-border bg-deep-space-black/50 p-4">
            <label className="block text-sm font-bold text-industrial-steel-blue uppercase mb-3">
              Position Preview
            </label>
            <div className="flex items-end space-x-2 h-32">
              {[1, 2, 3, 4, 5, 6].map((servoIndex) => {
                const pwm = editedFrame.servos[servoIndex];
                const percentage = ((pwm - 500) / 2000) * 100;
                
                return (
                  <div key={servoIndex} className="flex-1 flex flex-col items-center space-y-2">
                    <div className="flex-1 w-full bg-deep-space-black border border-industrial-steel-blue/30 rounded-cyberpunk relative">
                      <div
                        className="absolute bottom-0 left-0 right-0 bg-neon-magenta/50 transition-all duration-200"
                        style={{ height: `${percentage}%` }}
                      />
                      <div
                        className="absolute left-1/2 w-4 h-4 bg-neon-magenta rounded-full transform -translate-x-1/2 shadow-neon-glow"
                        style={{ bottom: `${percentage}%`, transform: 'translate(-50%, 50%)' }}
                      />
                    </div>
                    <span className="text-xs text-industrial-steel-blue">S{servoIndex}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-industrial-steel-blue/30 p-6 flex justify-end space-x-3">
          <CyberpunkButton
            onClick={onCancel}
            variant="secondary"
            disabled={isLoading}
          >
            CANCEL
          </CyberpunkButton>
          <CyberpunkButton
            onClick={handleSave}
            variant="primary"
            disabled={isLoading || Object.keys(errors).length > 0}
          >
            {isLoading ? 'SAVING...' : 'SAVE CHANGES'}
          </CyberpunkButton>
        </div>
      </div>

      {/* MP3 Assignment Modal */}
      <MP3AssignmentModal
        isOpen={showMP3Modal}
        currentSoundId={editedFrame.soundId}
        onClose={() => setShowMP3Modal(false)}
        onAssign={handleMP3Assign}
        onTestCommand={handleMP3TestCommand}
      />
    </div>
  );
};

export default FrameEditor;
