import type { ActionFrame, ActionProject } from '../shared/types';

describe('IPCClient demo mode', () => {
  const originalElectronAPI = (window as typeof window & { electronAPI?: unknown }).electronAPI;

  beforeEach(() => {
    jest.resetModules();
    (window as typeof window & { electronAPI?: unknown }).electronAPI = undefined;
  });

  afterEach(() => {
    if (originalElectronAPI === undefined) {
      (window as typeof window & { electronAPI?: unknown }).electronAPI = undefined;
    } else {
      (window as typeof window & { electronAPI?: unknown }).electronAPI = originalElectronAPI;
    }
  });

  test('stores created projects in memory when Electron API is unavailable', async () => {
    let IPCClientCtor: typeof import('../renderer/ipc-client').IPCClient;

    jest.isolateModules(() => {
      ({ IPCClient: IPCClientCtor } = require('../renderer/ipc-client'));
    });

    const client = new IPCClientCtor();
    const draftProject = {
      name: 'Demo Project',
      frames: [],
      createdAt: 100,
      modifiedAt: 100,
    };

    const projectId = await client.createProject(draftProject);
    const projects = await client.getAllProjects();

    expect(projects).toHaveLength(1);
    expect(projects[0]).toEqual<ActionProject>({
      id: projectId,
      ...draftProject,
    });
  });

  test('supports frame CRUD in demo mode so timeline actions work in browser fallback', async () => {
    let IPCClientCtor: typeof import('../renderer/ipc-client').IPCClient;

    jest.isolateModules(() => {
      ({ IPCClient: IPCClientCtor } = require('../renderer/ipc-client'));
    });

    const client = new IPCClientCtor();
    const projectId = await client.createProject({
      name: 'Timeline Demo',
      frames: [],
      createdAt: 100,
      modifiedAt: 100,
    });

    const frameA: ActionFrame = {
      sequenceId: 0,
      duration: 1000,
      servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 },
    };
    const frameB: ActionFrame = {
      sequenceId: 1,
      duration: 800,
      servos: { 1: 1200, 2: 1300, 3: 1400, 4: 1500, 5: 1600, 6: 1700 },
    };

    await client.addFrame(projectId, frameA);
    await client.addFrame(projectId, frameB);

    const afterAdd = await client.getProject(projectId);
    expect(afterAdd?.frames).toHaveLength(2);
    expect(afterAdd?.frames.map((frame) => frame.sequenceId)).toEqual([0, 1]);

    await client.reorderFrames(projectId, [1, 0]);
    const afterReorder = await client.getProject(projectId);
    expect(afterReorder?.frames[0].duration).toBe(800);
    expect(afterReorder?.frames.map((frame) => frame.sequenceId)).toEqual([0, 1]);

    await client.deleteFrame(projectId, 0);
    const afterDelete = await client.getProject(projectId);
    expect(afterDelete?.frames).toHaveLength(1);
    expect(afterDelete?.frames[0].duration).toBe(1000);
    expect(afterDelete?.frames[0].sequenceId).toBe(0);
  });
});
