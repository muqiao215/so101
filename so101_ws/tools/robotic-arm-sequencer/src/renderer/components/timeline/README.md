# Timeline Components

## Component Hierarchy

```
TimelineEditorScreen
├── Top Bar
│   ├── Back Button
│   ├── Project Name
│   ├── Undo Button
│   └── Redo Button
├── TimelineHeader
│   ├── Metadata Display
│   │   ├── Total Frames
│   │   ├── Total Duration
│   │   └── Average Frame Time
│   ├── Add Frame Button
│   └── Keyboard Shortcuts Reference
├── FrameList
│   └── Frame Cards (for each frame)
│       ├── Drag Handle (⋮⋮)
│       ├── Frame Number
│       ├── FrameThumbnail
│       │   └── 6 Servo Bars
│       ├── Frame Info
│       │   ├── Duration
│       │   └── Sound ID (if present)
│       └── Action Buttons
│           ├── Edit
│           ├── Copy
│           └── Delete
└── FrameEditor (Modal Dialog)
    ├── Header
    ├── Duration Control
    ├── Servo Position Sliders (6)
    ├── Sound ID Input
    ├── Position Preview
    └── Footer (Save/Cancel)
```

## Component Descriptions

### TimelineEditorScreen
**Purpose:** Main container and state management for timeline editing.

**Responsibilities:**
- Manage selected frame state
- Handle frame CRUD operations via IPC
- Coordinate undo/redo operations
- Handle keyboard shortcuts
- Manage loading states

**Props:**
- `project: ActionProject` - Current project being edited
- `onProjectChange: (project: ActionProject) => void` - Callback when project changes
- `onBack: () => void` - Callback to return to project list

### TimelineHeader
**Purpose:** Display sequence metadata and provide quick actions.

**Responsibilities:**
- Calculate and display total frames
- Calculate and display total duration
- Calculate and display average frame time
- Provide add frame button
- Show keyboard shortcuts reference

**Props:**
- `totalFrames: number` - Total number of frames
- `totalDuration: number` - Total duration in milliseconds
- `onAddFrame: () => void` - Callback to add new frame
- `isLoading?: boolean` - Loading state

### FrameList
**Purpose:** Display list of frames with drag-and-drop reordering.

**Responsibilities:**
- Render frame cards
- Handle drag-and-drop interactions
- Manage drag state and visual feedback
- Provide frame actions (edit, copy, delete)
- Show empty state when no frames

**Props:**
- `frames: ActionFrame[]` - Array of frames to display
- `selectedFrameIndex: number | null` - Currently selected frame index
- `onFrameSelect: (index: number) => void` - Callback when frame is selected
- `onFrameEdit: (index: number) => void` - Callback when frame is edited
- `onFrameDelete: (index: number) => void` - Callback when frame is deleted
- `onFrameDuplicate: (index: number) => void` - Callback when frame is duplicated
- `onFrameReorder: (fromIndex: number, toIndex: number) => void` - Callback when frames are reordered
- `isLoading?: boolean` - Loading state

### FrameThumbnail
**Purpose:** Visualize servo positions in a compact format.

**Responsibilities:**
- Display 6 servo position bars
- Show PWM values
- Indicate center position (1500µs)
- Provide visual feedback with neon magenta markers

**Props:**
- `frame: ActionFrame` - Frame to visualize

### FrameEditor
**Purpose:** Modal dialog for editing frame properties.

**Responsibilities:**
- Provide duration input and slider
- Provide 6 servo position sliders
- Provide optional sound ID input
- Validate all inputs
- Show real-time position preview
- Handle save/cancel actions

**Props:**
- `frame: ActionFrame` - Frame being edited
- `onSave: (frame: ActionFrame) => void` - Callback to save changes
- `onCancel: () => void` - Callback to cancel editing
- `isLoading?: boolean` - Loading state

## Usage Examples

### Basic Usage

```typescript
import TimelineEditorScreen from './screens/TimelineEditorScreen';

function App() {
  const [project, setProject] = useState<ActionProject>(/* ... */);
  
  return (
    <TimelineEditorScreen
      project={project}
      onProjectChange={setProject}
      onBack={() => console.log('Back to projects')}
    />
  );
}
```

### Using Individual Components

```typescript
import { TimelineHeader, FrameList, FrameEditor } from './components/timeline';

function CustomTimeline() {
  const [frames, setFrames] = useState<ActionFrame[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  
  return (
    <div>
      <TimelineHeader
        totalFrames={frames.length}
        totalDuration={frames.reduce((sum, f) => sum + f.duration, 0)}
        onAddFrame={() => {/* add frame logic */}}
      />
      
      <FrameList
        frames={frames}
        selectedFrameIndex={selectedIndex}
        onFrameSelect={setSelectedIndex}
        onFrameEdit={(index) => {/* edit logic */}}
        onFrameDelete={(index) => {/* delete logic */}}
        onFrameDuplicate={(index) => {/* duplicate logic */}}
        onFrameReorder={(from, to) => {/* reorder logic */}}
      />
    </div>
  );
}
```

## Styling

All components use Tailwind CSS with the cyberpunk theme. Key classes:

### Layout
- `cyberpunk-panel` - Panel background
- `cyberpunk-border` - Sharp-edged border
- `rounded-cyberpunk` - Sharp border radius (max 4px)

### Colors
- `bg-deep-space-black` - Deep Space Black (#0D0D0D)
- `bg-night-blue` - Night Blue (#1A1A2E)
- `text-industrial-steel-blue` - Industrial Steel Blue (#0F3460)
- `text-neon-magenta` - Neon Magenta (#E94560)
- `text-titanium-white` - Titanium White (#FFFFFF)

### Effects
- `shadow-neon-glow` - Neon glow effect
- `neon-text` - Neon magenta text with glow
- `hud-text` - HUD-style text (uppercase, tracked)

### Transitions
- `transition-all duration-200` - Smooth transitions
- `transition-colors` - Color transitions only

## Accessibility

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Tab order follows visual order
- Focus states are clearly visible (neon magenta ring)
- Keyboard shortcuts are documented in UI

### Screen Readers
- Semantic HTML elements used throughout
- ARIA labels on interactive elements
- Alt text on visual indicators
- Status messages announced

### Color Contrast
- All text meets WCAG AA standards
- Neon magenta used sparingly for emphasis
- High contrast between text and background

## Performance

### Optimization Strategies
- React.memo for expensive components
- useCallback for event handlers
- Debounced updates during drag operations
- Virtualization planned for large lists (>50 frames)

### Best Practices
- Minimal re-renders
- Efficient state updates
- Background database operations
- Optimistic UI updates

## Testing

### Unit Tests
```typescript
describe('FrameList', () => {
  it('should render frames', () => {
    const frames = [/* test frames */];
    render(<FrameList frames={frames} /* ... */ />);
    expect(screen.getAllByRole('button')).toHaveLength(frames.length * 3);
  });
  
  it('should handle frame selection', () => {
    const onSelect = jest.fn();
    render(<FrameList onFrameSelect={onSelect} /* ... */ />);
    fireEvent.click(screen.getByText('Frame 0'));
    expect(onSelect).toHaveBeenCalledWith(0);
  });
});
```

### Integration Tests
```typescript
describe('TimelineEditorScreen', () => {
  it('should add frame', async () => {
    render(<TimelineEditorScreen project={testProject} /* ... */ />);
    fireEvent.click(screen.getByText('+ ADD FRAME'));
    await waitFor(() => {
      expect(screen.getByText('Frame 1')).toBeInTheDocument();
    });
  });
});
```

## Troubleshooting

### Common Issues

**Issue:** Drag-and-drop not working
- **Solution:** Ensure `draggable={true}` is set on frame cards
- **Solution:** Check that drag event handlers are properly bound

**Issue:** Keyboard shortcuts not working
- **Solution:** Verify event listeners are attached to window
- **Solution:** Check that focus is not trapped in input fields

**Issue:** Frame editor not closing
- **Solution:** Ensure Escape key handler is registered
- **Solution:** Check that modal state is properly managed

**Issue:** Undo/Redo buttons disabled
- **Solution:** Verify IPC handlers are implemented
- **Solution:** Check that undo/redo state is being updated

## Future Enhancements

### Planned Features
- [ ] Frame preview animation
- [ ] Bulk frame operations (multi-select)
- [ ] Frame templates/presets
- [ ] Timeline zoom controls
- [ ] Frame search/filter
- [ ] Frame comments/notes
- [ ] Timeline markers
- [ ] Frame grouping/folders

### Performance Improvements
- [ ] Virtualization for large lists
- [ ] Web Workers for heavy computations
- [ ] Memoization of expensive calculations
- [ ] Lazy loading of frame thumbnails

### Accessibility Improvements
- [ ] High contrast mode
- [ ] Reduced motion mode
- [ ] Screen reader optimizations
- [ ] Keyboard shortcut customization

## Contributing

When adding new features to timeline components:

1. Follow the existing component structure
2. Use Tailwind CSS with cyberpunk theme
3. Add TypeScript types for all props
4. Include JSDoc comments
5. Write unit tests
6. Update this README
7. Test keyboard navigation
8. Verify accessibility

## Resources

- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
- [Keyboard Event Reference](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
