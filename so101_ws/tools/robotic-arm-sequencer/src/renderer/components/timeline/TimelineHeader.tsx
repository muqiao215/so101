import React from 'react';

interface TimelineHeaderProps {
  totalFrames: number;
  totalDuration: number;
  onAddFrame: () => void;
  isLoading?: boolean;
}

const TimelineHeader: React.FC<TimelineHeaderProps> = ({
  totalFrames,
  totalDuration,
  onAddFrame,
  isLoading = false,
}) => {
  const formattedDuration = (totalDuration / 1000).toFixed(1);
  const averageFrameTime = totalFrames > 0 ? (totalDuration / totalFrames).toFixed(0) : '0';

  return (
    <section className="mx-6 mt-5 rounded-3xl border border-dim bg-card p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-dim bg-black/10 px-4 py-3">
            <div className="text-xs font-medium uppercase text-dim">Frames</div>
            <div className="mt-2 text-2xl font-semibold text-main">{totalFrames}</div>
          </div>
          <div className="rounded-2xl border border-dim bg-black/10 px-4 py-3">
            <div className="text-xs font-medium uppercase text-dim">Total duration</div>
            <div className="mt-2 text-2xl font-semibold text-main">{formattedDuration}s</div>
          </div>
          <div className="rounded-2xl border border-dim bg-black/10 px-4 py-3">
            <div className="text-xs font-medium uppercase text-dim">Average frame time</div>
            <div className="mt-2 text-2xl font-semibold text-main">{averageFrameTime}ms</div>
          </div>
        </div>

        <button
          onClick={onAddFrame}
          disabled={isLoading}
          className={`rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${isLoading
            ? 'cursor-not-allowed border-dim bg-black/10 text-dim'
            : 'border-primary bg-primary/10 text-primary hover:bg-primary hover:text-black'
            }`}
        >
          Add frame
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-dim">
        <span className="rounded-full border border-dim px-2.5 py-1">Arrow keys: navigate</span>
        <span className="rounded-full border border-dim px-2.5 py-1">Enter: edit</span>
        <span className="rounded-full border border-dim px-2.5 py-1">Delete: remove</span>
        <span className="rounded-full border border-dim px-2.5 py-1">Ctrl+Z: undo</span>
        <span className="rounded-full border border-dim px-2.5 py-1">Ctrl+Shift+Z: redo</span>
      </div>
    </section>
  );
};

export default TimelineHeader;
