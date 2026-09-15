import fc from 'fast-check';
import { SQLiteDatabase } from '../main/database';
import { ActionProject, ActionFrame } from '../shared/types';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

describe('Database Round-Trip Property Tests', () => {
  let database: SQLiteDatabase;
  let tempDbPath: string;
  let testCounter = 0;

  beforeEach(() => {
    // Create a temporary database file for each test
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'robotic-arm-test-'));
    tempDbPath = path.join(tempDir, `test-${testCounter++}.db`);
    database = new SQLiteDatabase(tempDbPath);
  });

  afterEach(() => {
    // Clean up database and temp directory
    database.close();
    if (fs.existsSync(tempDbPath)) {
      fs.unlinkSync(tempDbPath);
    }
    const tempDir = path.dirname(tempDbPath);
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // Custom Fast-Check arbitraries for generating test data
  const servoArbitrary = fc.record({
    1: fc.integer({ min: 500, max: 2500 }),
    2: fc.integer({ min: 500, max: 2500 }),
    3: fc.integer({ min: 500, max: 2500 }),
    4: fc.integer({ min: 500, max: 2500 }),
    5: fc.integer({ min: 500, max: 2500 }),
    6: fc.integer({ min: 500, max: 2500 })
  });

  const actionFrameArbitrary = fc.record({
    sequenceId: fc.integer({ min: 0, max: 100 }),
    duration: fc.integer({ min: 500, max: 5000 }),
    servos: servoArbitrary,
    soundId: fc.option(fc.integer({ min: 1, max: 255 }))
  }).map(data => ActionFrameFactory.create(data));

  const actionProjectArbitrary = fc.record({
    name: fc.string({ minLength: 1, maxLength: 50 }),
    frames: fc.array(actionFrameArbitrary, { minLength: 0, maxLength: 20 }),
    remoteSlotId: fc.constant(undefined) // Avoid remote slot conflicts in property tests
  }).map(data => {
    const project = ActionProjectFactory.create(data);
    // Ensure frames have consecutive sequence IDs
    project.frames = project.frames.map((frame, index) => ({
      ...frame,
      sequenceId: index
    }));
    return project;
  });

  // Feature: robotic-arm-sequencer, Property 4: Database Round-Trip Consistency
  test('Property 4: Database Round-Trip Consistency - saving and loading projects should preserve all data', () => {
    fc.assert(
      fc.property(actionProjectArbitrary, (originalProject: ActionProject) => {
        // Save the project to database
        database.saveActionProject(originalProject);
        
        // Load the project back from database
        const loadedProject = database.loadActionProject(originalProject.id);
        
        // Verify the project was loaded successfully
        expect(loadedProject).not.toBeNull();
        
        if (loadedProject) {
          // Verify all project properties are preserved (except timestamps which may be updated)
          expect(loadedProject.id).toBe(originalProject.id);
          expect(loadedProject.name).toBe(originalProject.name);
          expect(loadedProject.remoteSlotId).toBe(originalProject.remoteSlotId);
          // Note: timestamps may be updated by database operations, so we don't check exact equality
          expect(loadedProject.createdAt).toBeGreaterThan(0);
          expect(loadedProject.modifiedAt).toBeGreaterThan(0);
          
          // Verify frames array length
          expect(loadedProject.frames).toHaveLength(originalProject.frames.length);
          
          // Verify each frame is preserved
          originalProject.frames.forEach((originalFrame, index) => {
            const loadedFrame = loadedProject.frames[index];
            
            expect(loadedFrame.sequenceId).toBe(originalFrame.sequenceId);
            expect(loadedFrame.duration).toBe(originalFrame.duration);
            expect(loadedFrame.soundId).toBe(originalFrame.soundId);
            
            // Verify all servo positions
            for (let servoIndex = 1; servoIndex <= 6; servoIndex++) {
              expect(loadedFrame.servos[servoIndex]).toBe(originalFrame.servos[servoIndex]);
            }
          });
        }
      }),
      { 
        numRuns: 1000,
        verbose: true
      }
    );
  });

  test('Property 4 Extension: Empty project round-trip consistency', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (projectName: string) => {
          const emptyProject = ActionProjectFactory.create({
            name: projectName,
            frames: [],
            remoteSlotId: undefined
          });
          
          // Save empty project
          database.saveActionProject(emptyProject);
          
          // Load project back
          const loadedProject = database.loadActionProject(emptyProject.id);
          
          expect(loadedProject).not.toBeNull();
          
          if (loadedProject) {
            expect(loadedProject.id).toBe(emptyProject.id);
            expect(loadedProject.name).toBe(emptyProject.name);
            expect(loadedProject.remoteSlotId).toBeUndefined();
            expect(loadedProject.frames).toHaveLength(0);
            expect(loadedProject.createdAt).toBeGreaterThan(0);
            expect(loadedProject.modifiedAt).toBeGreaterThan(0);
          }
        }
      ),
      { 
        numRuns: 1000,
        verbose: true
      }
    );
  });

  // Unit tests for edge cases and error conditions
  describe('Unit Tests for Database Edge Cases', () => {
    test('should handle non-existent project gracefully', () => {
      const nonExistentId = 'non-existent-id';
      const result = database.loadActionProject(nonExistentId);
      expect(result).toBeNull();
    });

    test('should handle empty database gracefully', () => {
      const allProjects = database.loadAllActionProjects();
      expect(allProjects).toHaveLength(0);
    });

    test('should enforce unique project IDs', () => {
      const project1 = ActionProjectFactory.create({ name: 'Project 1' });
      const project2 = { ...project1, name: 'Project 2' }; // Same ID
      
      database.saveActionProject(project1);
      
      // Second save should update, not create duplicate
      database.saveActionProject(project2);
      
      const allProjects = database.loadAllActionProjects();
      expect(allProjects).toHaveLength(1);
      expect(allProjects[0].name).toBe('Project 2');
    });

    test('should enforce unique remote slot IDs', () => {
      const project1 = ActionProjectFactory.create({ name: 'Project 1', remoteSlotId: 1 });
      const project2 = ActionProjectFactory.create({ name: 'Project 2', remoteSlotId: 1 });
      
      database.saveActionProject(project1);
      
      expect(() => {
        database.saveActionProject(project2);
      }).toThrow();
    });

    test('should handle database statistics correctly', () => {
      const stats1 = database.getStats();
      expect(stats1.projectCount).toBe(0);
      expect(stats1.frameCount).toBe(0);
      expect(stats1.dbSize).toBeGreaterThan(0);
      
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          })
        ]
      });
      
      database.saveActionProject(project);
      
      const stats2 = database.getStats();
      expect(stats2.projectCount).toBe(1);
      expect(stats2.frameCount).toBe(1);
    });

    test('should handle project updates correctly', () => {
      const originalProject = ActionProjectFactory.create({
        name: 'Original Name',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          })
        ]
      });
      
      // Save original project
      database.saveActionProject(originalProject);
      
      // Update project
      const updatedProject = {
        ...originalProject,
        name: 'Updated Name',
        modifiedAt: Date.now()
      };
      
      // Save updated project
      database.saveActionProject(updatedProject);
      
      // Load project back
      const loadedProject = database.loadActionProject(originalProject.id);
      
      expect(loadedProject).not.toBeNull();
      expect(loadedProject!.name).toBe('Updated Name');
      expect(loadedProject!.frames).toHaveLength(1);
    });

    test('should handle multiple projects without conflicts', () => {
      const project1 = ActionProjectFactory.create({ name: 'Project 1' });
      const project2 = ActionProjectFactory.create({ name: 'Project 2' });
      const project3 = ActionProjectFactory.create({ name: 'Project 3' });
      
      database.saveActionProject(project1);
      database.saveActionProject(project2);
      database.saveActionProject(project3);
      
      const allProjects = database.loadAllActionProjects();
      expect(allProjects).toHaveLength(3);
      
      const projectNames = allProjects.map(p => p.name).sort();
      expect(projectNames).toEqual(['Project 1', 'Project 2', 'Project 3']);
    });
  });
});