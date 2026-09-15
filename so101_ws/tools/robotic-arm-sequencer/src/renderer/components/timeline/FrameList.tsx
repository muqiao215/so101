import React, { useRef, useState } from 'react';
import type { ActionFrame } from '../../../shared/types';
import FrameThumbnail from './FrameThumbnail';
import VirtualizedFrameList from './VirtualizedFrameList';

interface FrameListProps {
  frames: ActionFrame[];
  selectedFrameIndex: number | null;
  onFrameSelect: (index: number) => void;
  onFrameEdit: (index: number) => void;
  onFrameDelete: (index: number) => void;
  onFrameDuplicate: (index: number) => void;
  onFrameReorder: (fromIndex: number, toIndex: number) => void;
  isLoading?: boolean;
}

const VIRTUALIZATION_THRESHOLD = 50;

const FrameList: React.FC<FrameListProps> = (props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(600);

  React.useEffect(() => {
    if (containerRef.current) {
      setContainerHeight(containerRef.current.clientHeight);
    }
  }, []);

  if (props.frames.length > VIRTUALIZATION_THRESHOLD) {
    return (
      <div ref={containerRef} className="h-full">
        <VirtualizedFrameList {...props} height={containerHeight} />
      </div>
    );
  }

  return <RegularFrameList {...props} />;
};

const RegularFrameList: React.FC<FrameListProps> = ({
  frames,
  selectedFrameIndex,
  onFrameSelect,
  onFrameEdit,
  onFrameDelete,
  onFrameDuplicate,
  onFrameReorder,
  isLoading = false,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const dragCounter = useRef(0);

  const handleDragStart = (e: React.DragEvent, index: number) => {
    if (isLoading) {
      return;
    }

    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
    setTimeout(() => {
      const target = e.currentTarget as HTMLElement;
      target.style.opacity = '0.5';
    }, 0);
  };

  const handleDragEnd = (e: React.DragEvent) => {
    const target = e.currentTarget as HTMLElement;
    target.style.opacity = '1';
    setDraggedIndex(null);
    setDragOverIndex(null);
    dragCounter.current = 0;
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (draggedIndex !== null && draggedIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDragEnter = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    dragCounter.current += 1;
    if (draggedIndex !== null && draggedIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDragLeave = () => {
    dragCounter.current -= 1;
    if (dragCounter.current === 0) {
      setDragOverIndex(null);
    }
  };

  const handleDrop = (e: React.DragEvent, toIndex: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== toIndex) {
      onFrameReorder(draggedIndex, toIndex);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
    dragCounter.current = 0;
  };

  if (frames.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 py-10">
        <div className="max-w-lg rounded-3xl border border-dim bg-card px-8 py-10 text-center">
          <p className="text-sm font-medium uppercase text-primary">Sequence is empty</p>
          <h2 className="mt-3 text-2xl font-semibold text-main">No frames yet</h2>
          <p className="mt-3 text-sm text-dim">
            Add the first frame to start building this sequence.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-6 pb-6">
      <div className="space-y-3">
        {frames.map((frame, index) => {
          const isSelected = selectedFrameIndex === index;
          const isDragging = draggedIndex === index;
          const isDragOver = dragOverIndex === index;

          return (
            <div
              key={`frame-${frame.sequenceId}-${index}`}
              draggable={!isLoading}
              onDragStart={(e) => handleDragStart(e, index)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnter={(e) => handleDragEnter(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onClick={() => onFrameSelect(index)}
              onDoubleClick={() => onFrameEdit(index)}
              className={`rounded-2xl border bg-card p-4 transition-colors ${isSelected
                ? 'border-primary bg-primary/5'
                : 'border-dim hover:border-primary/40'
                } ${isDragging ? 'opacity-50' : ''} ${isDragOver ? 'border-primary' : ''}`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
                <div className="flex items-center gap-4 lg:w-[220px]">
                  <div className="rounded-xl border border-dim px-3 py-2 text-center">
                    <div className="text-[11px] uppercase text-dim">Frame</div>
                    <div className="mt-1 text-xl font-semibold text-main">{frame.sequenceId}</div>
                  </div>
                  <div className="rounded-xl border border-dim px-3 py-2 text-center">
                    <div className="text-[11px] uppercase text-dim">Duration</div>
                    <div className="mt-1 text-base font-medium text-main">{frame.duration}ms</div>
                  </div>
                  <div className="text-xs text-dim">
                    Drag to reorder
                  </div>
                </div>

                <div className="min-w-0 flex-1">
                  <FrameThumbnail frame={frame} />
                </div>

                <div className="flex flex-wrap gap-2 lg:w-[280px] lg:justify-end">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onFrameEdit(index);
                    }}
                    disabled={isLoading}
                    className="rounded-xl border border-dim px-3 py-2 text-sm text-main transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onFrameDuplicate(index);
                    }}
                    disabled={isLoading}
                    className="rounded-xl border border-dim px-3 py-2 text-sm text-main transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
                  >
                    Duplicate
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onFrameDelete(index);
                    }}
                    disabled={isLoading}
                    className="rounded-xl border border-red-400/30 px-3 py-2 text-sm text-red-300 transition-colors hover:bg-red-500/10 hover:text-red-200 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FrameList;
