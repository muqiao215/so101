# Timeline Editor Visual Guide

## Overview

This guide provides a visual representation of the Timeline Editor interface and its components.

## Main Screen Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← BACK    PROJECT NAME                          ↶ UNDO    ↷ REDO       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Total Frames: 5    │  Total Duration: 5.0s  │  Avg: 1000ms    │    │
│  │                                                  [+ ADD FRAME]   │    │
│  ├────────────────────────────────────────────────────────────────┤    │
│  │  ↑↓ Navigate  Enter Edit  Del Delete  Ctrl+Z Undo  Ctrl+Shift+Z│    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ ⋮⋮  Frame 0  │ [Servo Bars] │ 1000ms  │ [EDIT] [COPY] [DEL]   │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ ⋮⋮  Frame 1  │ [Servo Bars] │ 1500ms ♪003 │ [EDIT] [COPY] [DEL]│    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ ⋮⋮  Frame 2  │ [Servo Bars] │ 2000ms  │ [EDIT] [COPY] [DEL]   │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Frame Card Detail

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⋮⋮    Frame 1                                                      │
│       ┌──┐                                                           │
│       │ 1│  [Servo Position Visualization]                          │
│       └──┘                                                           │
│                                                                      │
│  ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐                                          │
│  │█│ │█│ │█│ │█│ │█│ │█│  ← Position bars                         │
│  │█│ │▓│ │░│ │░│ │▓│ │█│                                           │
│  │▓│ │░│ │ │ │ │ │░│ │▓│                                           │
│  │░│ │ │ │ │ │ │ │ │ │░│                                           │
│  │─│ │─│ │─│ │─│ │─│ │─│  ← Center line (1500µs)                  │
│  │ │ │ │ │ │ │█│ │ │ │ │                                           │
│  │ │ │ │ │█│ │█│ │ │ │ │                                           │
│  │ │ │ │ │█│ │█│ │ │ │ │                                           │
│  └─┘ └─┘ └─┘ └─┘ └─┘ └─┘                                          │
│  S1  S2  S3  S4  S5  S6                                             │
│  2000 1800 1200 1700 1800 2100                                      │
│                                                                      │
│                                    Duration: 1500ms                 │
│                                    ♪ Track 003                      │
│                                                                      │
│                                    [EDIT] [COPY] [DEL]              │
└─────────────────────────────────────────────────────────────────────┘
```

## Frame Editor Dialog

```
┌─────────────────────────────────────────────────────────────────────┐
│  EDIT FRAME 1                                                   [X] │
│  Adjust servo positions, duration, and audio settings               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Frame Duration                                                      │
│  ┌──────┐                                                           │
│  │ 1500 │ milliseconds  [────────●──────────]                       │
│  └──────┘                                                           │
│  Valid range: 500-5000ms                                            │
│                                                                      │
│  Servo Positions                                                     │
│  ┌─────────────────────────┬─────────────────────────┐             │
│  │ SERVO 1        2000µs   │ SERVO 2        1800µs   │             │
│  │ [──────────●────────]   │ [────────●──────────]   │             │
│  │                         │                         │             │
│  │ SERVO 3        1200µs   │ SERVO 4        1700µs   │             │
│  │ [──●────────────────]   │ [───────●───────────]   │             │
│  │                         │                         │             │
│  │ SERVO 5        1800µs   │ SERVO 6        2100µs   │             │
│  │ [────────●──────────]   │ [───────────●───────]   │             │
│  └─────────────────────────┴─────────────────────────┘             │
│  Valid range: 500-2500µs (PWM pulse width)                          │
│                                                                      │
│  Audio Track (Optional)                                              │
│  ┌──────┐                                                           │
│  │  003 │ MP3 Track ID                                [Clear]       │
│  └──────┘                                                           │
│  Valid range: 1-255 (leave empty for no audio)                      │
│                                                                      │
│  Position Preview                                                    │
│  ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐                                          │
│  │█│ │█│ │░│ │▓│ │█│ │█│                                           │
│  │█│ │▓│ │ │ │░│ │▓│ │█│                                           │
│  │▓│ │░│ │ │ │ │ │░│ │▓│                                           │
│  │░│ │ │ │█│ │ │ │ │ │░│                                           │
│  └─┘ └─┘ └─┘ └─┘ └─┘ └─┘                                          │
│  S1  S2  S3  S4  S5  S6                                             │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                        [CANCEL]  [SAVE CHANGES]     │
└─────────────────────────────────────────────────────────────────────┘
```

## Drag-and-Drop Interaction

### Before Drag
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 1  │ [Bars] │ 1500ms │ [...] │  ← Dragging this
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 2  │ [Bars] │ 2000ms │ [...] │
└────────────────────────────────────────┘
```

### During Drag
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 2  │ [Bars] │ 2000ms │ [...] │  ← Drop indicator
╞════════════════════════════════════════╡  ← Neon magenta border
└────────────────────────────────────────┘

   ┌────────────────────────────────────┐
   │ Frame 1 │ [Bars] │ 1500ms │ [...] │  ← Dragging (50% opacity)
   └────────────────────────────────────┘
```

### After Drop
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 1  │ [Bars] │ 2000ms │ [...] │  ← Moved here
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 2  │ [Bars] │ 1500ms │ [...] │  ← Renumbered
└────────────────────────────────────────┘
```

## Selection States

### Unselected Frame
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │
└────────────────────────────────────────┘
```

### Selected Frame
```
╔════════════════════════════════════════╗  ← Neon magenta ring
║ ⋮⋮  Frame 1  │ [Bars] │ 1500ms │ [...] ║
╚════════════════════════════════════════╝
```

### Hover State
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 2  │ [Bars] │ 2000ms │ [...] │  ← Lighter background
└────────────────────────────────────────┘
```

## Empty State

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                                                                      │
│                       NO FRAMES IN SEQUENCE                          │
│                                                                      │
│              Click "ADD FRAME" to begin building your sequence       │
│                                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Background Colors
- **Deep Space Black** (#0D0D0D) - Main background
- **Night Blue** (#1A1A2E) - Panel backgrounds
- **Industrial Steel Blue** (#0F3460) - Borders and secondary elements

### Text Colors
- **Titanium White** (#FFFFFF) - Primary text
- **Industrial Steel Blue** (#0F3460) - Secondary text
- **Neon Magenta** (#E94560) - Accents and active states

### Visual Effects
- **Neon Glow** - Box shadow on active elements
- **Grid Pattern** - 5% opacity background grid
- **Sharp Edges** - Max 4px border radius

## Interaction Patterns

### Click Interactions
1. **Single Click** - Select frame
2. **Double Click** - Edit frame
3. **Button Click** - Perform action (Edit, Copy, Delete)

### Keyboard Interactions
1. **Arrow Keys** - Navigate between frames
2. **Enter** - Edit selected frame
3. **Delete** - Delete selected frame
4. **Ctrl+Z** - Undo last operation
5. **Ctrl+Shift+Z** - Redo operation
6. **Escape** - Close dialog

### Drag Interactions
1. **Drag Start** - Grab frame by handle (⋮⋮)
2. **Drag Over** - Show drop indicator
3. **Drop** - Reorder frames

## Responsive Behavior

### Desktop (1920x1080)
- Full timeline view
- All controls visible
- Optimal spacing

### Laptop (1366x768)
- Compact timeline view
- Scrollable frame list
- Reduced spacing

### Tablet (1024x768)
- Touch-friendly controls
- Larger hit areas
- Simplified layout

## Accessibility Features

### Visual
- High contrast text
- Clear focus indicators
- Color-blind friendly (not relying on color alone)

### Keyboard
- Full keyboard navigation
- Visible focus states
- Logical tab order

### Screen Reader
- Semantic HTML
- ARIA labels
- Status announcements

## Performance Indicators

### Loading State
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│         Loading...                     │  ← Loading indicator
└────────────────────────────────────────┘
```

### Disabled State
```
┌────────────────────────────────────────┐
│ ⋮⋮  Frame 0  │ [Bars] │ 1000ms │ [...] │  ← Reduced opacity
└────────────────────────────────────────┘
```

## Animation Timing

- **Transitions** - 200ms ease-in-out
- **Hover Effects** - Instant
- **Drag Feedback** - Instant
- **Modal Open/Close** - 150ms
- **Loading Spinner** - Continuous rotation

## Grid Background Pattern

```
┌─────────────────────────────────────────┐
│ · · · · · · · · · · · · · · · · · · · · │
│ · · · · · · · · · · · · · · · · · · · · │
│ · · · · · · · · · · · · · · · · · · · · │
│ · · · · · · · · · · · · · · · · · · · · │
│ · · · · · · · · · · · · · · · · · · · · │
│ · · · · · · · · · · · · · · · · · · · · │
└─────────────────────────────────────────┘
```
*20px x 20px grid with 5% opacity neon magenta*

## Neon Glow Effect

```
Normal State:
┌────────────┐
│   Button   │
└────────────┘

Active State:
┌────────────┐
│   Button   │  ← Neon magenta glow
└────────────┘
   ╰─────╯
```

## Summary

The Timeline Editor provides a comprehensive, cyberpunk-styled interface for editing robotic arm sequences. Key visual elements include:

- Sharp-edged design with max 4px border radius
- Neon magenta accents for active states
- Grid background patterns for technical feel
- Smooth transitions for all interactions
- Clear visual hierarchy
- Accessible keyboard navigation
- Responsive drag-and-drop feedback

All components work together to create an immersive, efficient editing experience that matches the cyberpunk aesthetic while maintaining usability and accessibility.
