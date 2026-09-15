import fc from 'fast-check';
import { ActionProjectFactory } from '../shared/factories';
import { ActionProject } from '../shared/types';

describe('Property Tests - Project Setup', () => {
  
  // Feature: robotic-arm-sequencer, Property 2: Project ID Uniqueness
  test('Property 2: Project ID Uniqueness - All generated project IDs should be unique', () => {
    fc.assert(fc.property(
      fc.array(fc.string({ minLength: 1, maxLength: 100 }), { minLength: 2, maxLength: 100 }),
      (projectNames) => {
        // Create multiple projects
        const projects = projectNames.map(name => 
          ActionProjectFactory.create({ name })
        );
        
        // Extract all project IDs
        const projectIds = projects.map(project => project.id);
        
        // Check that all IDs are unique
        const uniqueIds = new Set(projectIds);
        
        return uniqueIds.size === projectIds.length;
      }
    ), { numRuns: 1000 });
  });

  test('Property 2: Project ID Uniqueness - Sequential project creation should generate unique IDs', () => {
    fc.assert(fc.property(
      fc.integer({ min: 2, max: 50 }),
      fc.string({ minLength: 1, maxLength: 50 }),
      (count, baseName) => {
        const projects: ActionProject[] = [];
        
        // Create projects sequentially
        for (let i = 0; i < count; i++) {
          const project = ActionProjectFactory.create({ 
            name: `${baseName}_${i}` 
          });
          projects.push(project);
        }
        
        // Extract all project IDs
        const projectIds = projects.map(project => project.id);
        
        // Check that all IDs are unique
        const uniqueIds = new Set(projectIds);
        
        return uniqueIds.size === projectIds.length;
      }
    ), { numRuns: 1000 });
  });

  test('Property 2: Project ID Uniqueness - Concurrent project creation should generate unique IDs', () => {
    fc.assert(fc.property(
      fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 2, maxLength: 20 }),
      (projectNames) => {
        // Create projects concurrently (simulate rapid creation)
        const projects = projectNames.map(name => {
          return ActionProjectFactory.create({ name });
        });
        
        // Extract all project IDs
        const projectIds = projects.map(project => project.id);
        
        // Check that all IDs are unique
        const uniqueIds = new Set(projectIds);
        
        // Also verify that all IDs are valid UUIDs (basic format check)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        const allValidUUIDs = projectIds.every(id => uuidRegex.test(id));
        
        return uniqueIds.size === projectIds.length && allValidUUIDs;
      }
    ), { numRuns: 1000 });
  });
});