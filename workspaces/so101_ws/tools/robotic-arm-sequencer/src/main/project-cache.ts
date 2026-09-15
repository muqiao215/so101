/**
 * Project Cache Manager
 * Implements LRU (Least Recently Used) caching for frequently accessed projects
 * Reduces database queries and improves performance
 */

import { ActionProject } from '../shared/types';

interface CacheEntry {
  project: ActionProject;
  lastAccessed: number;
  accessCount: number;
}

export class ProjectCache {
  private cache: Map<string, CacheEntry>;
  private maxSize: number;
  private hitCount: number = 0;
  private missCount: number = 0;

  constructor(maxSize: number = 20) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }

  /**
   * Get project from cache
   */
  get(id: string): ActionProject | null {
    const entry = this.cache.get(id);
    
    if (entry) {
      // Update access statistics
      entry.lastAccessed = Date.now();
      entry.accessCount++;
      this.hitCount++;
      
      // Return a deep copy to prevent external modifications
      return this.deepCopy(entry.project);
    }
    
    this.missCount++;
    return null;
  }

  /**
   * Put project in cache
   */
  set(id: string, project: ActionProject): void {
    // If cache is full, evict least recently used entry
    if (this.cache.size >= this.maxSize && !this.cache.has(id)) {
      this.evictLRU();
    }

    // Store a deep copy to prevent external modifications
    this.cache.set(id, {
      project: this.deepCopy(project),
      lastAccessed: Date.now(),
      accessCount: 1
    });
  }

  /**
   * Remove project from cache
   */
  delete(id: string): void {
    this.cache.delete(id);
  }

  /**
   * Clear entire cache
   */
  clear(): void {
    this.cache.clear();
    this.hitCount = 0;
    this.missCount = 0;
  }

  /**
   * Check if project is in cache
   */
  has(id: string): boolean {
    return this.cache.has(id);
  }

  /**
   * Get cache size
   */
  size(): number {
    return this.cache.size;
  }

  /**
   * Get cache hit rate
   */
  getHitRate(): number {
    const total = this.hitCount + this.missCount;
    return total === 0 ? 0 : this.hitCount / total;
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number;
    maxSize: number;
    hitCount: number;
    missCount: number;
    hitRate: number;
  } {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hitCount: this.hitCount,
      missCount: this.missCount,
      hitRate: this.getHitRate()
    };
  }

  /**
   * Evict least recently used entry
   */
  private evictLRU(): void {
    let oldestId: string | null = null;
    let oldestTime = Infinity;

    // Find entry with oldest lastAccessed time
    for (const [id, entry] of this.cache.entries()) {
      if (entry.lastAccessed < oldestTime) {
        oldestTime = entry.lastAccessed;
        oldestId = id;
      }
    }

    if (oldestId) {
      this.cache.delete(oldestId);
    }
  }

  /**
   * Deep copy helper to prevent cache pollution
   */
  private deepCopy(project: ActionProject): ActionProject {
    return {
      ...project,
      frames: project.frames.map(frame => ({
        ...frame,
        servos: { ...frame.servos }
      }))
    };
  }

  /**
   * Warm up cache with frequently accessed projects
   */
  warmUp(projects: ActionProject[]): void {
    // Sort by modified date (most recent first)
    const sorted = [...projects].sort((a, b) => b.modifiedAt - a.modifiedAt);
    
    // Add up to maxSize projects to cache
    const toCache = sorted.slice(0, this.maxSize);
    toCache.forEach(project => {
      this.set(project.id, project);
    });
  }

  /**
   * Invalidate cache entries older than specified age (in milliseconds)
   */
  invalidateOld(maxAge: number): number {
    const now = Date.now();
    let invalidated = 0;

    for (const [id, entry] of this.cache.entries()) {
      if (now - entry.lastAccessed > maxAge) {
        this.cache.delete(id);
        invalidated++;
      }
    }

    return invalidated;
  }

  /**
   * Get most frequently accessed projects
   */
  getMostAccessed(count: number = 5): Array<{ id: string; accessCount: number }> {
    const entries = Array.from(this.cache.entries());
    
    return entries
      .map(([id, entry]) => ({ id, accessCount: entry.accessCount }))
      .sort((a, b) => b.accessCount - a.accessCount)
      .slice(0, count);
  }
}
