import React, { useState, useEffect } from 'react';
import ComponentShowcase from './components/ComponentShowcase';
import ProjectListScreen from './screens/ProjectListScreen';
import TimelineEditorScreen from './screens/TimelineEditorScreen';
import RealTimeControlScreen from './screens/RealTimeControlScreen';
import { NotificationProvider } from './contexts/NotificationContext';
import ToastContainer from './components/ToastContainer';
import type { ActionProject, ActionFrame } from '../shared/types';

interface AppState {
  isConnected: boolean;
  appVersion: string;
  currentProject: ActionProject | null;
  currentView: 'projectList' | 'timeline' | 'realtime';
}

const App: React.FC = () => {
  const [state, setState] = useState<AppState>({
    isConnected: false,
    appVersion: '1.0.0',
    currentProject: null,
    currentView: 'projectList'
  });

  // Check if we should show the component showcase
  const showShowcase = new URLSearchParams(window.location.search).get('showcase') === 'true';

  useEffect(() => {
    // Get app version on startup
    if (window.electronAPI) {
      window.electronAPI.getVersion().then(version => {
        setState(prev => ({ ...prev, appVersion: version }));
      });
    }
  }, []);

  const handleProjectOpen = async (project: ActionProject) => {
    // Center servos when opening a project (safety feature)
    try {
      const connected = await window.electronAPI?.serial?.isConnected?.();
      if (connected) {
        // Use type assertion for sendRawCommand (defined in preload but TS doesn't see it)
        const serial = window.electronAPI?.serial as any;
        await serial?.sendRawCommand?.('CENTER');
        console.log('Servos centered on project open');
      }
    } catch (error) {
      console.warn('Could not center servos:', error);
    }

    setState(prev => ({
      ...prev,
      currentProject: project,
      currentView: 'timeline'
    }));
  };

  const handleBackToProjects = () => {
    setState(prev => ({
      ...prev,
      currentProject: null,
      currentView: 'projectList'
    }));
  };

  const handleProjectChange = (project: ActionProject) => {
    setState(prev => ({
      ...prev,
      currentProject: project
    }));
  };

  const handleFrameCapture = (frame: ActionFrame) => {
    if (!state.currentProject) return;

    const updatedProject: ActionProject = {
      ...state.currentProject,
      frames: [...state.currentProject.frames, frame],
      modifiedAt: Date.now()
    };

    setState(prev => ({
      ...prev,
      currentProject: updatedProject
    }));

    // Save to database via IPC
    if (window.electronAPI) {
      window.electronAPI.project.update(updatedProject).catch((error: Error) => {
        console.error('Failed to save captured frame:', error);
      });
    }
  };

  const handleSwitchToRealtime = () => {
    setState(prev => ({
      ...prev,
      currentView: 'realtime'
    }));
  };

  const handleSwitchToTimeline = () => {
    setState(prev => ({
      ...prev,
      currentView: 'timeline'
    }));
  };

  // Show component showcase if requested
  if (showShowcase) {
    return (
      <NotificationProvider>
        <ComponentShowcase />
        <ToastContainer />
      </NotificationProvider>
    );
  }

  // Show project list screen
  if (state.currentView === 'projectList') {
    return (
      <NotificationProvider>
        <ProjectListScreen onProjectOpen={handleProjectOpen} />
        <ToastContainer />
      </NotificationProvider>
    );
  }

  // Show timeline editor screen
  if (state.currentView === 'timeline' && state.currentProject) {
    return (
      <NotificationProvider>
        <TimelineEditorScreen
          project={state.currentProject}
          onProjectChange={handleProjectChange}
          onBack={handleBackToProjects}
        />
        <ToastContainer />
      </NotificationProvider>
    );
  }

  // Show real-time control screen
  if (state.currentView === 'realtime') {
    return (
      <NotificationProvider>
        <RealTimeControlScreen
          project={state.currentProject || undefined}
          onFrameCapture={handleFrameCapture}
          onBack={state.currentProject ? handleSwitchToTimeline : handleBackToProjects}
        />
        <ToastContainer />
      </NotificationProvider>
    );
  }

  // Original timeline/realtime view (placeholder for now)
  return (
    <NotificationProvider>
      <div className="cyberpunk-container w-full h-full flex flex-col">
        {/* Status Bar */}
        <div className="cyberpunk-panel flex justify-between items-center h-12 px-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBackToProjects}
              className="text-industrial-steel-blue hover:text-neon-magenta transition-colors text-sm"
            >
              ← BACK TO PROJECTS
            </button>
            <h1 className="text-lg font-bold neon-text">
              {state.currentProject?.name || 'ROBOTIC ARM SEQUENCER'}
            </h1>
            <span className="hud-text">v{state.appVersion}</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className={`status-indicator ${state.isConnected ? 'status-connected' : 'status-disconnected'}`}></div>
              <span className="hud-text">
                {state.isConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex">
          {/* Left Panel - Project List */}
          <div className="w-80 cyberpunk-panel m-2">
            <h2 className="text-sm font-bold mb-4 hud-text">PROJECT LIBRARY</h2>
            <div className="space-y-2">
              <div className="cyberpunk-border p-3 bg-deep-space-black">
                <div className="text-sm font-bold">Sample Project</div>
                <div className="text-xs text-industrial-steel-blue">5 frames • 2.5s duration</div>
              </div>
            </div>
            <button className="cyberpunk-button w-full mt-4">
              + NEW PROJECT
            </button>
          </div>

          {/* Center Panel - Timeline Editor */}
          <div className="flex-1 cyberpunk-panel m-2">
            <h2 className="text-sm font-bold mb-4 hud-text">TIMELINE EDITOR</h2>
            <div className="h-full flex flex-col">
              {/* Timeline Header */}
              <div className="cyberpunk-border p-3 mb-4 bg-deep-space-black">
                <div className="flex justify-between items-center">
                  <div className="text-xs hud-text">SEQUENCE: UNTITLED</div>
                  <div className="text-xs hud-text">0 FRAMES • 0.0s TOTAL</div>
                </div>
              </div>

              {/* Timeline Content */}
              <div className="flex-1 cyberpunk-border bg-deep-space-black p-4">
                <div className="text-center text-industrial-steel-blue">
                  No frames in sequence. Add frames to begin.
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Real-time Controls */}
          <div className="w-80 cyberpunk-panel m-2">
            <h2 className="text-sm font-bold mb-4 hud-text">REAL-TIME CONTROL</h2>

            {/* Servo Controls */}
            <div className="space-y-4 mb-6">
              {[1, 2, 3, 4, 5, 6].map(servo => (
                <div key={servo} className="cyberpunk-border p-3 bg-deep-space-black">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs hud-text">SERVO {servo}</span>
                    <span className="text-xs font-mono">1500µs</span>
                  </div>
                  <input
                    type="range"
                    min="500"
                    max="2500"
                    defaultValue="1500"
                    className="w-full h-2 bg-industrial-steel-blue rounded-cyberpunk appearance-none"
                  />
                </div>
              ))}
            </div>

            {/* Emergency Stop */}
            <button className="cyberpunk-button w-full bg-red-600 hover:bg-red-500 animate-electric-pulse">
              EMERGENCY STOP [DISARMED]
            </button>
          </div>
        </div>

        {/* Bottom Panel - Execution Controls */}
        <div className="cyberpunk-panel h-16 flex items-center justify-center space-x-4">
          <button className="cyberpunk-button">▶ PLAY</button>
          <button className="cyberpunk-button">⏸ PAUSE</button>
          <button className="cyberpunk-button">⏹ STOP</button>
          <button className="cyberpunk-button">🔄 LOOP</button>
          <div className="flex-1 mx-4">
            <div className="cyberpunk-border bg-deep-space-black h-4 relative">
              <div className="bg-neon-magenta h-full w-0 transition-all duration-300"></div>
            </div>
          </div>
          <span className="text-xs hud-text">0% COMPLETE</span>
        </div>
        <ToastContainer />
      </div>
    </NotificationProvider>
  );
};

export default App;