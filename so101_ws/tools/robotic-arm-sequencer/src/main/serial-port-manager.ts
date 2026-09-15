import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { SerialError, TimeoutError, PortInfo } from '../shared/types';

/**
 * SerialPortManager handles all serial communication with Arduino
 * Provides connection management, command sending, and error recovery
 */
export class SerialPortManager {
  private port: SerialPort | null = null;
  private parser: ReadlineParser | null = null;
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000; // ms
  
  // Event callbacks
  private onDataCallback?: (data: string) => void;
  private onErrorCallback?: (error: Error) => void;
  private onDisconnectCallback?: () => void;
  
  /**
   * Connect to a serial port
   */
  async connect(portPath: string, baudRate: number = 115200): Promise<void> {
    if (this.isConnected) {
      throw new SerialError('Already connected to a port');
    }
    
    try {
      this.port = new SerialPort({
        path: portPath,
        baudRate,
        dataBits: 8,
        parity: 'none',
        stopBits: 1
      });
      
      // Set up line parser for Arduino responses
      this.parser = this.port.pipe(new ReadlineParser({ delimiter: '\r\n' }));
      
      // Set up event handlers
      this.setupEventHandlers();
      
      // Wait for port to open
      await new Promise<void>((resolve, reject) => {
        this.port!.on('open', () => {
          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve();
        });
        
        this.port!.on('error', (error) => {
          reject(new SerialError(`Failed to connect: ${error.message}`));
        });
      });
      
    } catch (error) {
      throw new SerialError(`Connection failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * Disconnect from the serial port
   */
  async disconnect(): Promise<void> {
    if (!this.port || !this.isConnected) {
      return;
    }
    
    try {
      await new Promise<void>((resolve, reject) => {
        this.port!.close((error) => {
          if (error) {
            reject(new SerialError(`Disconnect failed: ${error.message}`));
          } else {
            this.isConnected = false;
            this.port = null;
            this.parser = null;
            resolve();
          }
        });
      });
    } catch (error) {
      throw new SerialError(`Disconnect failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * Send a command without expecting a response
   */
  async sendCommand(command: string): Promise<void> {
    if (!this.isConnected || !this.port) {
      throw new SerialError('Not connected to any port');
    }
    
    try {
      await new Promise<void>((resolve, reject) => {
        this.port!.write(command + '\n', (error) => {
          if (error) {
            reject(new SerialError(`Failed to send command: ${error.message}`));
          } else {
            resolve();
          }
        });
      });
    } catch (error) {
      throw new SerialError(`Send command failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * Send a command and wait for response with timeout
   */
  async sendCommandWithResponse(command: string, timeout: number = 5000): Promise<string> {
    if (!this.isConnected || !this.port || !this.parser) {
      throw new SerialError('Not connected to any port');
    }
    
    return new Promise<string>((resolve, reject) => {
      if (!this.parser || !this.port) {
        reject(new SerialError('Not connected to any port'));
        return;
      }
      
      const timer = setTimeout(() => {
        reject(new TimeoutError(`Command timed out after ${timeout}ms: ${command}`));
      }, timeout);
      
      // Set up one-time response handler
      const responseHandler = (data: string) => {
        clearTimeout(timer);
        if (this.parser) {
          this.parser.off('data', responseHandler);
        }
        resolve(data.trim());
      };
      
      this.parser.on('data', responseHandler);
      
      // Send the command
      this.port.write(command + '\n', (error) => {
        if (error) {
          clearTimeout(timer);
          if (this.parser) {
            this.parser.off('data', responseHandler);
          }
          reject(new SerialError(`Failed to send command: ${error.message}`));
        }
      });
    });
  }
  
  /**
   * Send command with retry logic
   */
  async sendCommandWithRetry(command: string, maxRetries: number = 3): Promise<void> {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        await this.sendCommand(command);
        return;
      } catch (error) {
        if (attempt === maxRetries - 1) {
          throw new SerialError(
            `Failed after ${maxRetries} attempts: ${error instanceof Error ? error.message : String(error)}`
          );
        }
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }
  
  /**
   * Send command with response and timeout
   */
  async sendCommandWithTimeout(command: string, timeout: number = 5000): Promise<string> {
    return this.sendCommandWithResponse(command, timeout);
  }
  
  /**
   * Check if port is connected
   */
  isPortConnected(): boolean {
    return this.isConnected && this.port !== null && this.port.isOpen;
  }
  
  /**
   * List all available serial ports
   */
  async listAvailablePorts(): Promise<PortInfo[]> {
    try {
      const ports = await SerialPort.list();
      return ports.map(port => ({
        path: port.path,
        manufacturer: port.manufacturer,
        serialNumber: port.serialNumber,
        pnpId: port.pnpId,
        locationId: port.locationId,
        productId: port.productId,
        vendorId: port.vendorId
      }));
    } catch (error) {
      throw new SerialError(`Failed to list ports: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  /**
   * Set up event handlers for the serial port
   */
  private setupEventHandlers(): void {
    if (!this.port || !this.parser) return;
    
    // Handle incoming data
    this.parser.on('data', (data: string) => {
      if (this.onDataCallback) {
        this.onDataCallback(data.trim());
      }
    });
    
    // Handle port errors
    this.port.on('error', (error) => {
      const serialError = new SerialError(`Port error: ${error.message}`);
      if (this.onErrorCallback) {
        this.onErrorCallback(serialError);
      }
      this.handleConnectionError(serialError);
    });
    
    // Handle port close/disconnect
    this.port.on('close', () => {
      this.isConnected = false;
      if (this.onDisconnectCallback) {
        this.onDisconnectCallback();
      }
      this.handleDisconnection();
    });
  }
  
  /**
   * Handle connection errors with recovery logic
   */
  private handleConnectionError(error: Error): void {
    console.error('Serial connection error:', error);
    this.isConnected = false;
    
    // Attempt reconnection if not at max attempts
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.attemptReconnection();
    }
  }
  
  /**
   * Handle disconnection events
   */
  private handleDisconnection(): void {
    console.log('Serial port disconnected');
    this.isConnected = false;
    this.port = null;
    this.parser = null;
  }
  
  /**
   * Attempt to reconnect to the last known port
   */
  private async attemptReconnection(): Promise<void> {
    if (!this.port) return;
    
    const portPath = this.port.path;
    
    this.reconnectAttempts++;
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
    
    setTimeout(async () => {
      try {
        await this.disconnect();
        await this.connect(portPath);
        console.log('Reconnection successful');
      } catch (error) {
        console.error('Reconnection failed:', error);
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnection();
        } else {
          console.error('Max reconnection attempts reached');
          if (this.onErrorCallback) {
            this.onErrorCallback(new SerialError('Connection lost and reconnection failed'));
          }
        }
      }
    }, this.reconnectDelay);
  }
  
  /**
   * Set callback for incoming data
   */
  onData(callback: (data: string) => void): void {
    this.onDataCallback = callback;
  }
  
  /**
   * Set callback for errors
   */
  onError(callback: (error: Error) => void): void {
    this.onErrorCallback = callback;
  }
  
  /**
   * Set callback for disconnection
   */
  onDisconnect(callback: () => void): void {
    this.onDisconnectCallback = callback;
  }
  
  /**
   * Get current port information
   */
  getPortInfo(): PortInfo | null {
    if (!this.port) return null;
    
    return {
      path: this.port.path,
      // Additional info would be available from the original port list
    };
  }
  
  /**
   * Send emergency stop command
   */
  async sendEmergencyStop(): Promise<void> {
    await this.sendCommand('EMERGENCY_STOP');
  }
  
  /**
   * Send disarm command
   */
  async sendDisarmCommand(): Promise<void> {
    await this.sendCommand('DISARM');
  }
}