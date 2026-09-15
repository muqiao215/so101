import Database from 'better-sqlite3';
import { 
  ActionProject, 
  ActionFrame, 
  ProjectEntity, 
  FrameEntity, 
  DatabaseError, 
  DuplicateProjectError 
} from '../shared/types';
import { randomUUID } from 'crypto';
import * as path from 'path';
import * as fs from 'fs';

export class SQLiteDatabase {
  private db: Database.Database;
  private dbPath: string;

  constructor(dbPath?: string) {
    // Default to user data directory if no path provided
    this.dbPath = dbPath || path.join(process.cwd(), 'data', 'robotic-arm-sequencer.db');
    
    // Ensure directory exists
    const dbDir = path.dirname(this.dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    try {
      this.db = new Database(this.dbPath);
      this.db.pragma('journal_mode = WAL');
      this.db.pragma('foreign_keys = ON');
      this.initializeTables();
    } catch (error) {
      throw new DatabaseError(this.formatInitializationError(error));
    }
  }

  private formatInitializationError(error: unknown): string {
    const message = error instanceof Error ? error.message : String(error);

    if (this.isNativeBindingMismatch(message)) {
      return [
        `Failed to initialize database: ${message}`,
        'The better-sqlite3 native binding does not match the current runtime.',
        'Run `npm run rebuild:native` from this environment and retry.'
      ].join(' ');
    }

    return `Failed to initialize database: ${message}`;
  }

  private isNativeBindingMismatch(message: string): boolean {
    return (
      message.includes('invalid ELF header') ||
      message.includes('not a valid Win32 application') ||
      message.includes('wrong ELF class') ||
      message.includes('Exec format error')
    );
  }

  private initializeTables(): void {
    try {
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          remote_slot_id INTEGER,
          created_at INTEGER NOT NULL,
          modified_at INTEGER NOT NULL,
          CONSTRAINT unique_remote_slot UNIQUE (remote_slot_id),
          CONSTRAINT valid_remote_slot CHECK (remote_slot_id IS NULL OR (remote_slot_id >= 1 AND remote_slot_id <= 10))
        );
        
        CREATE TABLE IF NOT EXISTS frames (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL,
          sequence_id INTEGER NOT NULL,
          duration INTEGER NOT NULL,
          servo1 INTEGER NOT NULL,
          servo2 INTEGER NOT NULL,
          servo3 INTEGER NOT NULL,
          servo4 INTEGER NOT NULL,
          servo5 INTEGER NOT NULL,
          servo6 INTEGER NOT NULL,
          sound_id INTEGER,
          FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
          CONSTRAINT valid_duration CHECK (duration >= 500 AND duration <= 5000),
          CONSTRAINT valid_servo1 CHECK (servo1 >= 500 AND servo1 <= 2500),
          CONSTRAINT valid_servo2 CHECK (servo2 >= 500 AND servo2 <= 2500),
          CONSTRAINT valid_servo3 CHECK (servo3 >= 500 AND servo3 <= 2500),
          CONSTRAINT valid_servo4 CHECK (servo4 >= 500 AND servo4 <= 2500),
          CONSTRAINT valid_servo5 CHECK (servo5 >= 500 AND servo5 <= 2500),
          CONSTRAINT valid_servo6 CHECK (servo6 >= 500 AND servo6 <= 2500),
          CONSTRAINT valid_sound_id CHECK (sound_id IS NULL OR (sound_id >= 1 AND sound_id <= 255)),
          CONSTRAINT unique_project_sequence UNIQUE (project_id, sequence_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_frames_project_sequence 
        ON frames (project_id, sequence_id);
        
        CREATE INDEX IF NOT EXISTS idx_projects_name 
        ON projects (name);
        
        CREATE INDEX IF NOT EXISTS idx_projects_modified 
        ON projects (modified_at DESC);
        
        CREATE INDEX IF NOT EXISTS idx_projects_remote_slot 
        ON projects (remote_slot_id) WHERE remote_slot_id IS NOT NULL;
        
        CREATE INDEX IF NOT EXISTS idx_frames_project_id 
        ON frames (project_id);
      `);
    } catch (error) {
      throw new DatabaseError(`Failed to create database schema: ${(error as Error).message}`);
    }
  }

  // Transaction support
  executeTransaction<T>(operations: () => T): T {
    const transaction = this.db.transaction(() => {
      try {
        return operations();
      } catch (error) {
        throw new DatabaseError(`Transaction failed: ${(error as Error).message}`);
      }
    });
    
    return transaction();
  }

  // Project CRUD Operations
  insertProject(project: ProjectEntity): void {
    try {
      const stmt = this.db.prepare(`
        INSERT INTO projects (id, name, remote_slot_id, created_at, modified_at)
        VALUES (?, ?, ?, ?, ?)
      `);
      
      stmt.run(
        project.id,
        project.name,
        project.remote_slot_id || null,
        project.created_at,
        project.modified_at
      );
    } catch (error: any) {
      if (error.code === 'SQLITE_CONSTRAINT_PRIMARYKEY') {
        throw new DuplicateProjectError(`Project with ID ${project.id} already exists`);
      }
      if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
        throw new DatabaseError(`Remote slot ${project.remote_slot_id} is already in use`);
      }
      throw new DatabaseError(`Failed to insert project: ${(error as Error).message}`);
    }
  }

  getProject(id: string): ProjectEntity | null {
    try {
      const stmt = this.db.prepare(`
        SELECT id, name, remote_slot_id, created_at, modified_at
        FROM projects 
        WHERE id = ?
      `);
      
      const result = stmt.get(id) as ProjectEntity | undefined;
      return result || null;
    } catch (error) {
      throw new DatabaseError(`Failed to get project: ${(error as Error).message}`);
    }
  }

  getAllProjects(): ProjectEntity[] {
    try {
      const stmt = this.db.prepare(`
        SELECT id, name, remote_slot_id, created_at, modified_at
        FROM projects 
        ORDER BY modified_at DESC
      `);
      
      return stmt.all() as ProjectEntity[];
    } catch (error) {
      throw new DatabaseError(`Failed to get all projects: ${(error as Error).message}`);
    }
  }

  /**
   * Get project metadata with frame count (lazy loading - no frame data)
   */
  getProjectMetadata(id: string): { project: ProjectEntity; frameCount: number } | null {
    try {
      const projectStmt = this.db.prepare(`
        SELECT id, name, remote_slot_id, created_at, modified_at
        FROM projects 
        WHERE id = ?
      `);
      
      const project = projectStmt.get(id) as ProjectEntity | undefined;
      if (!project) {
        return null;
      }

      const countStmt = this.db.prepare(`
        SELECT COUNT(*) as count FROM frames WHERE project_id = ?
      `);
      
      const result = countStmt.get(id) as { count: number };
      
      return {
        project,
        frameCount: result.count
      };
    } catch (error) {
      throw new DatabaseError(`Failed to get project metadata: ${(error as Error).message}`);
    }
  }

  /**
   * Get all projects metadata with frame counts (lazy loading)
   */
  getAllProjectsMetadata(): Array<{ project: ProjectEntity; frameCount: number; totalDuration: number }> {
    try {
      const stmt = this.db.prepare(`
        SELECT 
          p.id, 
          p.name, 
          p.remote_slot_id, 
          p.created_at, 
          p.modified_at,
          COUNT(f.id) as frame_count,
          COALESCE(SUM(f.duration), 0) as total_duration
        FROM projects p
        LEFT JOIN frames f ON p.id = f.project_id
        GROUP BY p.id
        ORDER BY p.modified_at DESC
      `);
      
      const results = stmt.all() as Array<{
        id: string;
        name: string;
        remote_slot_id?: number;
        created_at: number;
        modified_at: number;
        frame_count: number;
        total_duration: number;
      }>;

      return results.map(row => ({
        project: {
          id: row.id,
          name: row.name,
          remote_slot_id: row.remote_slot_id,
          created_at: row.created_at,
          modified_at: row.modified_at
        },
        frameCount: row.frame_count,
        totalDuration: row.total_duration
      }));
    } catch (error) {
      throw new DatabaseError(`Failed to get all projects metadata: ${(error as Error).message}`);
    }
  }

  updateProject(project: ProjectEntity): void {
    try {
      const stmt = this.db.prepare(`
        UPDATE projects 
        SET name = ?, remote_slot_id = ?, modified_at = ?
        WHERE id = ?
      `);
      
      const result = stmt.run(
        project.name,
        project.remote_slot_id || null,
        project.modified_at,
        project.id
      );
      
      if (result.changes === 0) {
        throw new DatabaseError(`Project with ID ${project.id} not found`);
      }
    } catch (error: any) {
      if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
        throw new DatabaseError(`Remote slot ${project.remote_slot_id} is already in use`);
      }
      throw new DatabaseError(`Failed to update project: ${(error as Error).message}`);
    }
  }

  deleteProject(id: string): void {
    try {
      const stmt = this.db.prepare('DELETE FROM projects WHERE id = ?');
      const result = stmt.run(id);
      
      if (result.changes === 0) {
        throw new DatabaseError(`Project with ID ${id} not found`);
      }
    } catch (error) {
      throw new DatabaseError(`Failed to delete project: ${(error as Error).message}`);
    }
  }

  // Frame CRUD Operations
  insertFrame(frame: FrameEntity): void {
    try {
      const stmt = this.db.prepare(`
        INSERT INTO frames (
          id, project_id, sequence_id, duration, 
          servo1, servo2, servo3, servo4, servo5, servo6, sound_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      stmt.run(
        frame.id,
        frame.project_id,
        frame.sequence_id,
        frame.duration,
        frame.servo1,
        frame.servo2,
        frame.servo3,
        frame.servo4,
        frame.servo5,
        frame.servo6,
        frame.sound_id || null
      );
    } catch (error: any) {
      if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
        throw new DatabaseError(`Frame with sequence ID ${frame.sequence_id} already exists in project ${frame.project_id}`);
      }
      if (error.code === 'SQLITE_CONSTRAINT_FOREIGNKEY') {
        throw new DatabaseError(`Project with ID ${frame.project_id} does not exist`);
      }
      throw new DatabaseError(`Failed to insert frame: ${(error as Error).message}`);
    }
  }

  getFramesByProject(projectId: string): FrameEntity[] {
    try {
      const stmt = this.db.prepare(`
        SELECT id, project_id, sequence_id, duration,
               servo1, servo2, servo3, servo4, servo5, servo6, sound_id
        FROM frames 
        WHERE project_id = ?
        ORDER BY sequence_id ASC
      `);
      
      return stmt.all(projectId) as FrameEntity[];
    } catch (error) {
      throw new DatabaseError(`Failed to get frames for project: ${(error as Error).message}`);
    }
  }

  updateFrame(frame: FrameEntity): void {
    try {
      const stmt = this.db.prepare(`
        UPDATE frames 
        SET duration = ?, servo1 = ?, servo2 = ?, servo3 = ?, 
            servo4 = ?, servo5 = ?, servo6 = ?, sound_id = ?
        WHERE id = ?
      `);
      
      const result = stmt.run(
        frame.duration,
        frame.servo1,
        frame.servo2,
        frame.servo3,
        frame.servo4,
        frame.servo5,
        frame.servo6,
        frame.sound_id || null,
        frame.id
      );
      
      if (result.changes === 0) {
        throw new DatabaseError(`Frame with ID ${frame.id} not found`);
      }
    } catch (error) {
      throw new DatabaseError(`Failed to update frame: ${(error as Error).message}`);
    }
  }

  deleteFrame(id: string): void {
    try {
      const stmt = this.db.prepare('DELETE FROM frames WHERE id = ?');
      const result = stmt.run(id);
      
      if (result.changes === 0) {
        throw new DatabaseError(`Frame with ID ${id} not found`);
      }
    } catch (error) {
      throw new DatabaseError(`Failed to delete frame: ${(error as Error).message}`);
    }
  }

  deleteFramesByProject(projectId: string): void {
    try {
      const stmt = this.db.prepare('DELETE FROM frames WHERE project_id = ?');
      stmt.run(projectId);
    } catch (error) {
      throw new DatabaseError(`Failed to delete frames for project: ${(error as Error).message}`);
    }
  }

  // Utility methods for data conversion
  projectEntityToActionProject(entity: ProjectEntity, frames: FrameEntity[]): ActionProject {
    const actionFrames: ActionFrame[] = frames.map(frame => ({
      sequenceId: frame.sequence_id,
      duration: frame.duration,
      servos: {
        1: frame.servo1,
        2: frame.servo2,
        3: frame.servo3,
        4: frame.servo4,
        5: frame.servo5,
        6: frame.servo6
      },
      soundId: frame.sound_id || undefined
    }));

    return {
      id: entity.id,
      name: entity.name,
      remoteSlotId: entity.remote_slot_id || undefined,
      frames: actionFrames,
      createdAt: entity.created_at,
      modifiedAt: entity.modified_at
    };
  }

  actionProjectToEntities(project: ActionProject): { projectEntity: ProjectEntity; frameEntities: FrameEntity[] } {
    const projectEntity: ProjectEntity = {
      id: project.id,
      name: project.name,
      remote_slot_id: project.remoteSlotId || undefined,
      created_at: project.createdAt,
      modified_at: project.modifiedAt
    };

    const frameEntities: FrameEntity[] = project.frames.map(frame => ({
      id: randomUUID(),
      project_id: project.id,
      sequence_id: frame.sequenceId,
      duration: frame.duration,
      servo1: frame.servos[1],
      servo2: frame.servos[2],
      servo3: frame.servos[3],
      servo4: frame.servos[4],
      servo5: frame.servos[5],
      servo6: frame.servos[6],
      sound_id: frame.soundId || undefined
    }));

    return { projectEntity, frameEntities };
  }

  // High-level operations that combine project and frame operations
  saveActionProject(project: ActionProject): void {
    this.executeTransaction(() => {
      const { projectEntity, frameEntities } = this.actionProjectToEntities(project);
      
      // Check if project exists
      const existingProject = this.getProject(project.id);
      
      if (existingProject) {
        // Update existing project
        this.updateProject(projectEntity);
        // Delete existing frames and insert new ones
        this.deleteFramesByProject(project.id);
      } else {
        // Insert new project
        this.insertProject(projectEntity);
      }
      
      // Insert all frames
      frameEntities.forEach(frame => {
        this.insertFrame(frame);
      });
    });
  }

  loadActionProject(id: string): ActionProject | null {
    try {
      const projectEntity = this.getProject(id);
      if (!projectEntity) {
        return null;
      }
      
      const frameEntities = this.getFramesByProject(id);
      return this.projectEntityToActionProject(projectEntity, frameEntities);
    } catch (error) {
      throw new DatabaseError(`Failed to load action project: ${(error as Error).message}`);
    }
  }

  loadAllActionProjects(): ActionProject[] {
    try {
      const projectEntities = this.getAllProjects();
      return projectEntities.map(projectEntity => {
        const frameEntities = this.getFramesByProject(projectEntity.id);
        return this.projectEntityToActionProject(projectEntity, frameEntities);
      });
    } catch (error) {
      throw new DatabaseError(`Failed to load all action projects: ${(error as Error).message}`);
    }
  }

  // Database management
  close(): void {
    try {
      this.db.close();
    } catch (error) {
      throw new DatabaseError(`Failed to close database: ${(error as Error).message}`);
    }
  }

  // Migration support
  getCurrentVersion(): number {
    try {
      const stmt = this.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'");
      const result = stmt.get();
      
      if (!result) {
        // Create version table if it doesn't exist
        this.db.exec(`
          CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY
          );
          INSERT INTO schema_version (version) VALUES (1);
        `);
        return 1;
      }
      
      const versionStmt = this.db.prepare('SELECT version FROM schema_version LIMIT 1');
      const versionResult = versionStmt.get() as { version: number } | undefined;
      return versionResult?.version || 1;
    } catch (error) {
      throw new DatabaseError(`Failed to get database version: ${(error as Error).message}`);
    }
  }

  updateVersion(version: number): void {
    try {
      const stmt = this.db.prepare('UPDATE schema_version SET version = ?');
      stmt.run(version);
    } catch (error) {
      throw new DatabaseError(`Failed to update database version: ${(error as Error).message}`);
    }
  }

  // Database statistics and health checks
  getStats(): { projectCount: number; frameCount: number; dbSize: number } {
    try {
      const projectCountStmt = this.db.prepare('SELECT COUNT(*) as count FROM projects');
      const frameCountStmt = this.db.prepare('SELECT COUNT(*) as count FROM frames');
      
      const projectCount = (projectCountStmt.get() as { count: number }).count;
      const frameCount = (frameCountStmt.get() as { count: number }).count;
      
      const stats = fs.statSync(this.dbPath);
      const dbSize = stats.size;
      
      return { projectCount, frameCount, dbSize };
    } catch (error) {
      throw new DatabaseError(`Failed to get database stats: ${(error as Error).message}`);
    }
  }

  vacuum(): void {
    try {
      this.db.exec('VACUUM');
    } catch (error) {
      throw new DatabaseError(`Failed to vacuum database: ${(error as Error).message}`);
    }
  }
}
