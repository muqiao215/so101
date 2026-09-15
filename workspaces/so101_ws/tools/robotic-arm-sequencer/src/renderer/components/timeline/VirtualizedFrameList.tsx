/**
 * Virtualized Frame List Component
 * Uses react-window for efficient rendering of large frame lists (>50 items)
 * Only renders visible frames to maintain 60 FPS performance
 */

import React, { useState, useRef, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import type { ActionFrame } from '../../../shared/types';
import FrameThumbnail from './FrameThumbnail';

interface VirtualizedFrameListProps {
  frames: ActionFrame[];
  selectedFrameIndex: number | null;
  onFrameSelect: (index: number) => void;
  onFrameEdit: (index: number) => void;
  onFrameDelete: (index: number) => void;
  onFrameDuplicate: (index: number) => void;
  onFrameReorder: (fromIndex: number, toIndex: number) => void;
  isLoading?: boolean;
  height: number; // Container height for virtualization
}

const FRAME_HEIGHT = 120; // Height of each frame card in pixels

const VirtualizedFrameList: React.FC<VirtualizedFrameListProps> = ({
  frames,
  selectedFrameIndex,
  onFrameSelect,
  onFrameEdit,
  onFrameDelete,
  onFrameDuplicate,
  onFrameReorder,
  isLoading = false,
  height
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const listRef = useRef<List>(null);

  // Row renderer for react-window
  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const frame = frames[index];
    const isSelected = selectedFrameIndex === index;
    const isDragging = draggedIndex === index;
    const isDragOver = dragOverIndex === index;

    const handleDragStart = (e: React.DragEvent) => {
      if (isLoading) return;
      setDraggedIndex(index);
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', index.toString());
    };

    const handleDragEnd = () => {
      setDraggedIndex(null);
      setDragOverIndex(null);
    };

    const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (draggedIndex !== null && draggedIndex !== index) {
        setDragOverIndex(index);
      }
    };

    const handleDrop = (e: React.DragEvent) => {
      e.preventDefault();
      if (draggedIndex !== null && draggedIndex !== index) {
        onFrameReorder(draggedIndex, index);
      }
      setDraggedIndex(null);
      setDragOverIndex(null);
    };

    return (
      <div style={style} className="px-4 py-1">
        <div
          draggable={!isLoading}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => onFrameSelect(index)}
          onDoubleClick={() => onFrameEdit(index)}
          className={`
            cyberpunk-border bg-night-blue/50 p-4 cursor-pointer
            transition-all duration-200
            ${isSelected ? 'ring-2 ring-neon-magenta shadow-neon-glow' : 'hover:bg-night-blue/70'}
            ${isDragging ? 'opacity-50' : ''}
            ${isDragOver ? 'border-neon-magenta border-2' : ''}
          `}
        >
          <div className="flex items-center space-x-4">
            {/* Drag Handle */}
            <div className="flex flex-col items-center justify-center w-8 text-industrial-steel-blue hover:text-neon-magenta transition-colors">
              <div className="text-xs">⋮⋮</div>
            </div>
            
            {/* Frame Number */}
            <div className="flex flex-col items-center justify-center w-16">
              <span className="text-xs text-industrial-steel-blue uppercase">Frame</span>
              <span className="text-2xl font-bold font-mono neon-text">
                {frame.sequenceId}
              </span>
            </div>
            
            {/* Frame Thumbnail */}
            <div className="flex-1">
              <FrameThumbnail frame={frame} />
            </div>
            
            {/* Frame Info */}
            <div className="flex flex-col items-end space-y-1 w-32">
              <div className="text-xs text-industrial-steel-blue">
                Duration
              </div>
              <div className="text-lg font-mono neon-text">
                {frame.duration}ms
              </div>
              {frame.soundId && (
                <div className="text-xs text-neon-magenta flex items-center space-x-1">
                  <span>♪</span>
                  <span>Track {frame.soundId.toString().padStart(3, '0')}</span>
                </div>
              )}
            </div>
            
            {/* Actions */}
            <div className="flex flex-col space-y-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onFrameEdit(index);
                }}
                disabled={isLoading}
                className="px-2 py-1 text-xs bg-industrial-steel-blue/30 hover:bg-industrial-steel-blue/50 
                  text-titanium-white rounded-cyberpunk transition-colors disabled:opacity-50"
                title="Edit Frame"
              >
                EDIT
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onFrameDuplicate(index);
                }}
                disabled={isLoading}
                className="px-2 py-1 text-xs bg-industrial-steel-blue/30 hover:bg-industrial-steel-blue/50 
                  text-titanium-white rounded-cyberpunk transition-colors disabled:opacity-50"
                title="Duplicate Frame"
              >
                COPY
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onFrameDelete(index);
                }}
                disabled={isLoading}
                className="px-2 py-1 text-xs bg-red-900/30 hover:bg-red-900/50 
                  text-red-400 rounded-cyberpunk transition-colors disabled:opacity-50"
                title="Delete Frame"
              >
                DEL
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }, [frames, selectedFrameIndex, draggedIndex, dragOverIndex, isLoading, onFrameSelect, onFrameEdit, onFrameDelete, onFrameDuplicate, onFrameReorder]);

  // Empty state
  if (frames.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-industrial-steel-blue text-lg">
            NO FRAMES IN SEQUENCE
          </div>
          <div className="text-industrial-steel-blue/70 text-sm">
            Click "ADD FRAME" to begin building your sequence
          </div>
        </div>
      </div>
    );
  }

  // Scroll to selected frame when it changes
  React.useEffect(() => {
    if (selectedFrameIndex !== null && listRef.current) {
      listRef.current.scrollToItem(selectedFrameIndex, 'smart');
    }
  }, [selectedFrameIndex]);

  return (
    <div className="h-full relative">
      {/* Grid Background Pattern */}
      <div className="absolute inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(to right, #E94560 1px, transparent 1px),
            linear-gradient(to bottom, #E94560 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px'
        }}
      />
      
      {/* Virtualized List */}
      <List
        ref={listRef}
        height={height}
        itemCount={frames.length}
        itemSize={FRAME_HEIGHT}
        width="100%"
        overscanCount={5} // Render 5 extra items above/below viewport for smooth scrolling
      >
        {Row}
      </List>
    </div>
  );
};

export default VirtualizedFrameList;
