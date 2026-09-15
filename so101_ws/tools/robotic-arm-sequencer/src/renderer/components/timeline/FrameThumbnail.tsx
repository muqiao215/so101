/**
 * Frame Thumbnail Component
 * Visualizes servo positions in a compact format
 */

import React from 'react';
import type { ActionFrame } from '../../../shared/types';

interface FrameThumbnailProps {
  frame: ActionFrame;
}

const FrameThumbnail: React.FC<FrameThumbnailProps> = ({ frame }) => {
  // Calculate percentage for each servo (500-2500 range)
  const getServoPercentage = (pwm: number): number => {
    return ((pwm - 500) / 2000) * 100;
  };

  return (
    <div className="flex items-center space-x-2">
      {[1, 2, 3, 4, 5, 6].map((servoIndex) => {
        const pwm = frame.servos[servoIndex] || 1500;
        const percentage = getServoPercentage(pwm);
        
        return (
          <div key={servoIndex} className="flex flex-col items-center space-y-1 flex-1">
            {/* Servo Label */}
            <span className="text-[10px] text-industrial-steel-blue uppercase">
              S{servoIndex}
            </span>
            
            {/* Servo Bar */}
            <div className="w-full h-12 bg-deep-space-black border border-industrial-steel-blue/30 rounded-cyberpunk relative overflow-hidden">
              {/* Background Grid */}
              <div className="absolute inset-0 opacity-10"
                style={{
                  backgroundImage: `linear-gradient(to bottom, #E94560 1px, transparent 1px)`,
                  backgroundSize: '100% 25%'
                }}
              />
              
              {/* Center Line (1500µs) */}
              <div className="absolute left-0 right-0 top-1/2 h-px bg-industrial-steel-blue/50 transform -translate-y-1/2" />
              
              {/* Position Indicator */}
              <div
                className="absolute left-0 right-0 h-1 bg-neon-magenta shadow-neon-glow transition-all duration-200"
                style={{
                  top: `${100 - percentage}%`,
                  transform: 'translateY(-50%)'
                }}
              />
              
              {/* Position Marker */}
              <div
                className="absolute left-1/2 w-3 h-3 bg-neon-magenta rounded-full transform -translate-x-1/2 shadow-neon-glow"
                style={{
                  top: `${100 - percentage}%`,
                  transform: 'translate(-50%, -50%)'
                }}
              />
            </div>
            
            {/* PWM Value */}
            <span className="text-[10px] font-mono text-titanium-white">
              {pwm}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default FrameThumbnail;
