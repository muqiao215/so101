/**
 * Performance Optimizations Tests
 * Tests for virtualization, caching, database optimization, and performance monitoring
 */

import { ProjectCache } from '../main/project-cache';
import { SQLiteDatabase } from '../main/database';
import { ActionProjectFactory, ActionFrameFactory } from '../shared/factories';
import { PerformanceMonitor, debounce, throttle } from '../renderer/utils/performance-monitor';
import * as path from 'path';
import * as fs from 'fs';

describe('Performance Optimizations Tests', () => {
  
  // ==================== Cache Tests ====================
  
  describe('ProjectCache', () => {
    let cache: ProjectCache;

    beforeEach(() => {
      cache = new ProjectCache(5); // Small cache for testing
    });

    test('should cache and retrieve projects', () => {
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: []
      });

      cache.set(project.id, project);
      const retrieved = cache.get(project.id);

      expect(retrieved).not.toBeNull();
      expect(retrieved?.id).toBe(project.id);
      expect(retrieved?.name).toBe(project.name);
    });

    test('should return null for non-existent projects', () => {
      const result = cache.get('non-existent-id');
      expect(result).toBeNull();
    });

    test('should track cache hits and misses', () => {
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: []
      });

      cache.set(project.id, project);
      
      // Hit
      cache.get(project.id);
      
      // Miss
      cache.get('non-existent');

      const stats = cache.getStats();
      expect(stats.hitCount).toBe(1);
      expect(stats.missCount).toBe(1);
      expect(stats.hitRate).toBe(0.5);
    });

    test('should evict LRU entry when cache is full', () => {
      // Fill cache to capacity
      const projects = Array.from({ length: 5 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: []
        })
      );

      projects.forEach(p => cache.set(p.id, p));
      expect(cache.size()).toBe(5);

      // Access all but the first project to make it LRU
      projects.slice(1).forEach(p => cache.get(p.id));

      // Add new project, should evict first project
      const newProject = ActionProjectFactory.create({
        name: 'New Project',
        frames: []
      });
      cache.set(newProject.id, newProject);

      expect(cache.size()).toBe(5);
      expect(cache.has(projects[0].id)).toBe(false);
      expect(cache.has(newProject.id)).toBe(true);
    });

    test('should return deep copy to prevent cache pollution', () => {
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

      cache.set(project.id, project);
      const retrieved = cache.get(project.id);

      // Modify retrieved project
      if (retrieved) {
        retrieved.name = 'Modified Name';
        retrieved.frames[0].duration = 2000;
      }

      // Original in cache should be unchanged
      const retrievedAgain = cache.get(project.id);
      expect(retrievedAgain?.name).toBe('Test Project');
      expect(retrievedAgain?.frames[0].duration).toBe(1000);
    });

    test('should warm up cache with recent projects', () => {
      const projects = Array.from({ length: 10 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: []
        })
      );

      // Set different modified times
      projects.forEach((p, i) => {
        p.modifiedAt = Date.now() - (10 - i) * 1000;
      });

      cache.warmUp(projects);

      // Should cache only the 5 most recent (cache size = 5)
      expect(cache.size()).toBe(5);
      
      // Most recent projects should be cached
      expect(cache.has(projects[9].id)).toBe(true);
      expect(cache.has(projects[8].id)).toBe(true);
      expect(cache.has(projects[7].id)).toBe(true);
      expect(cache.has(projects[6].id)).toBe(true);
      expect(cache.has(projects[5].id)).toBe(true);
      
      // Oldest projects should not be cached
      expect(cache.has(projects[0].id)).toBe(false);
    });

    test('should invalidate old cache entries', (done) => {
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: []
      });

      cache.set(project.id, project);
      
      // Wait a bit
      const maxAge = 100; // 100ms
      
      setTimeout(() => {
        const invalidated = cache.invalidateOld(maxAge);
        expect(invalidated).toBeGreaterThanOrEqual(1); // At least 1 should be invalidated
        expect(cache.has(project.id)).toBe(false);
        done();
      }, maxAge + 50);
    });

    test('should track most accessed projects', () => {
      const projects = Array.from({ length: 3 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: []
        })
      );

      projects.forEach(p => cache.set(p.id, p));

      // Access projects different number of times
      // Note: set() counts as 1 access, so we need to account for that
      cache.get(projects[0].id); // 2 total (1 from set + 1 from get)
      cache.get(projects[1].id); // 3 total (1 from set + 2 from get)
      cache.get(projects[1].id);
      cache.get(projects[2].id); // 4 total (1 from set + 3 from get)
      cache.get(projects[2].id);
      cache.get(projects[2].id);

      const mostAccessed = cache.getMostAccessed(2);
      expect(mostAccessed[0].id).toBe(projects[2].id);
      expect(mostAccessed[0].accessCount).toBe(4); // 1 from set + 3 from get
      expect(mostAccessed[1].id).toBe(projects[1].id);
      expect(mostAccessed[1].accessCount).toBe(3); // 1 from set + 2 from get
    });
  });

  // ==================== Database Optimization Tests ====================
  
  describe('Database Optimizations', () => {
    let db: SQLiteDatabase;
    const testDbPath = path.join(__dirname, 'test-performance.db');

    beforeEach(() => {
      // Clean up any existing test database
      if (fs.existsSync(testDbPath)) {
        fs.unlinkSync(testDbPath);
      }
      db = new SQLiteDatabase(testDbPath);
    });

    afterEach(() => {
      db.close();
      if (fs.existsSync(testDbPath)) {
        fs.unlinkSync(testDbPath);
      }
    });

    test('should load project metadata without frames (lazy loading)', () => {
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: [
          ActionFrameFactory.create({
            sequenceId: 0,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          }),
          ActionFrameFactory.create({
            sequenceId: 1,
            duration: 2000,
            servos: { 1: 1600, 2: 1600, 3: 1600, 4: 1600, 5: 1600, 6: 1600 }
          })
        ]
      });

      db.saveActionProject(project);

      const metadata = db.getProjectMetadata(project.id);
      expect(metadata).not.toBeNull();
      expect(metadata?.project.id).toBe(project.id);
      expect(metadata?.project.name).toBe(project.name);
      expect(metadata?.frameCount).toBe(2);
    });

    test('should load all projects metadata with aggregated data', () => {
      const projects = Array.from({ length: 3 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: Array.from({ length: i + 1 }, (_, j) =>
            ActionFrameFactory.create({
              sequenceId: j,
              duration: 1000,
              servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
            })
          )
        })
      );

      projects.forEach(p => db.saveActionProject(p));

      const metadata = db.getAllProjectsMetadata();
      expect(metadata).toHaveLength(3);
      
      // Check frame counts
      expect(metadata.find(m => m.project.name === 'Project 0')?.frameCount).toBe(1);
      expect(metadata.find(m => m.project.name === 'Project 1')?.frameCount).toBe(2);
      expect(metadata.find(m => m.project.name === 'Project 2')?.frameCount).toBe(3);
      
      // Check total durations
      expect(metadata.find(m => m.project.name === 'Project 0')?.totalDuration).toBe(1000);
      expect(metadata.find(m => m.project.name === 'Project 1')?.totalDuration).toBe(2000);
      expect(metadata.find(m => m.project.name === 'Project 2')?.totalDuration).toBe(3000);
    });

    test('should perform fast queries with indexes', () => {
      // Create many projects to test index performance
      const projects = Array.from({ length: 50 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: Array.from({ length: 10 }, (_, j) =>
            ActionFrameFactory.create({
              sequenceId: j,
              duration: 1000,
              servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
            })
          )
        })
      );

      projects.forEach(p => db.saveActionProject(p));

      // Measure query time
      const startTime = performance.now();
      const metadata = db.getAllProjectsMetadata();
      const endTime = performance.now();
      const queryTime = endTime - startTime;

      expect(metadata).toHaveLength(50);
      expect(queryTime).toBeLessThan(100); // Should be fast with indexes
    });
  });

  // ==================== Performance Monitor Tests ====================
  
  describe('PerformanceMonitor', () => {
    let monitor: PerformanceMonitor;

    beforeEach(() => {
      monitor = new PerformanceMonitor();
    });

    afterEach(() => {
      monitor.stop();
    });

    test('should start and stop monitoring', () => {
      monitor.start();
      const metrics = monitor.getMetrics();
      expect(metrics.renderCount).toBeGreaterThanOrEqual(0);
      
      monitor.stop();
    });

    test('should track frame metrics', (done) => {
      monitor.start();
      
      setTimeout(() => {
        const metrics = monitor.getMetrics();
        expect(metrics.fps).toBeGreaterThan(0);
        expect(metrics.renderCount).toBeGreaterThan(0);
        monitor.stop();
        done();
      }, 100);
    });

    test('should calculate performance grade', () => {
      monitor.start();
      
      setTimeout(() => {
        const grade = monitor.getPerformanceGrade();
        expect(['excellent', 'good', 'fair', 'poor']).toContain(grade);
        monitor.stop();
      }, 100);
    });

    test('should reset metrics', () => {
      monitor.start();
      
      setTimeout(() => {
        monitor.reset();
        const metrics = monitor.getMetrics();
        expect(metrics.renderCount).toBe(0);
        expect(metrics.slowFrames).toBe(0);
        monitor.stop();
      }, 100);
    });
  });

  // ==================== Utility Function Tests ====================
  
  describe('Performance Utilities', () => {
    
    test('debounce should delay function execution', (done) => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 50);

      // Call multiple times rapidly
      debouncedFn();
      debouncedFn();
      debouncedFn();

      // Should not have been called yet
      expect(callCount).toBe(0);

      // Wait for debounce delay
      setTimeout(() => {
        expect(callCount).toBe(1); // Should only be called once
        done();
      }, 100);
    });

    test('throttle should limit function execution rate', (done) => {
      let callCount = 0;
      const throttledFn = throttle(() => {
        callCount++;
      }, 50);

      // Call multiple times rapidly
      throttledFn(); // Should execute immediately
      throttledFn(); // Should be throttled
      throttledFn(); // Should be throttled

      expect(callCount).toBe(1);

      // Wait for throttle period
      setTimeout(() => {
        throttledFn(); // Should execute after throttle period
        expect(callCount).toBe(2);
        done();
      }, 100);
    });
  });

  // ==================== Integration Tests ====================
  
  describe('Performance Integration', () => {
    let db: SQLiteDatabase;
    let cache: ProjectCache;
    const testDbPath = path.join(__dirname, 'test-integration.db');

    beforeEach(() => {
      if (fs.existsSync(testDbPath)) {
        fs.unlinkSync(testDbPath);
      }
      db = new SQLiteDatabase(testDbPath);
      cache = new ProjectCache(10);
    });

    afterEach(() => {
      db.close();
      if (fs.existsSync(testDbPath)) {
        fs.unlinkSync(testDbPath);
      }
    });

    test('should demonstrate cache performance improvement', () => {
      const project = ActionProjectFactory.create({
        name: 'Test Project',
        frames: Array.from({ length: 100 }, (_, i) =>
          ActionFrameFactory.create({
            sequenceId: i,
            duration: 1000,
            servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
          })
        )
      });

      db.saveActionProject(project);

      // First load (database query)
      const start1 = performance.now();
      const loaded1 = db.loadActionProject(project.id);
      const time1 = performance.now() - start1;

      // Cache it
      if (loaded1) {
        cache.set(loaded1.id, loaded1);
      }

      // Second load (from cache)
      const start2 = performance.now();
      const loaded2 = cache.get(project.id);
      const time2 = performance.now() - start2;

      expect(loaded2).not.toBeNull();
      expect(time2).toBeLessThan(time1); // Cache should be faster
      expect(time2).toBeLessThan(1); // Cache access should be < 1ms
    });

    test('should handle large project lists efficiently', () => {
      // Create 100 projects
      const projects = Array.from({ length: 100 }, (_, i) =>
        ActionProjectFactory.create({
          name: `Project ${i}`,
          frames: Array.from({ length: 5 }, (_, j) =>
            ActionFrameFactory.create({
              sequenceId: j,
              duration: 1000,
              servos: { 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500, 6: 1500 }
            })
          )
        })
      );

      projects.forEach(p => db.saveActionProject(p));

      // Load metadata (lazy loading)
      const startTime = performance.now();
      const metadata = db.getAllProjectsMetadata();
      const endTime = performance.now();
      const queryTime = endTime - startTime;

      expect(metadata).toHaveLength(100);
      expect(queryTime).toBeLessThan(200); // Should load quickly with indexes
    });
  });
});
