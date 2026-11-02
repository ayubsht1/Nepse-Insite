/**
 * Real-Time WebSocket Service for NEPSE Insight (/ws/updates/)
 * Handles automatic reconnection, message dispatching, and connection states.
 */

import { getAccessToken } from './api';

export type WebSocketConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface MarketUpdateEvent {
  event: string;
  data: Record<string, unknown>;
  occurred_at: string;
}

export type MessageHandler = (event: MarketUpdateEvent) => void;

class NepseWebSocketService {
  private socket: WebSocket | null = null;
  private status: WebSocketConnectionStatus = 'disconnected';
  private handlers: Set<MessageHandler> = new Set();
  private statusListeners: Set<(status: WebSocketConnectionStatus) => void> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: any = null;
  private shouldReconnect = true;

  private getWsUrl(): string {
    const configuredUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (configuredUrl) {
      return configuredUrl;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/updates/`;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      this.setStatus('disconnected');
      return;
    }

    this.shouldReconnect = true;
    this.setStatus('connecting');

    try {
      this.socket = new WebSocket(this.getWsUrl(), [
        'nepse-insight',
        `nepse-insight.bearer.${token}`,
      ]);

      this.socket.onopen = () => {
        this.setStatus('connected');
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (event) => {
        let parsed: MarketUpdateEvent;
        try {
          parsed = JSON.parse(event.data) as MarketUpdateEvent;
        } catch (err) {
          console.warn('Received non-JSON websocket message:', event.data);
          return;
        }
        this.handlers.forEach((handler) => handler(parsed));
      };

      this.socket.onerror = () => {
        this.setStatus('error');
      };

      this.socket.onclose = () => {
        this.setStatus('disconnected');
        if (this.shouldReconnect) {
          this.attemptReconnect();
        }
      };
    } catch (err) {
      this.setStatus('error');
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('Max WebSocket reconnection attempts reached. Idle fallback active.');
      return;
    }

    const backoffDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
    this.reconnectAttempts += 1;

    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, backoffDelay);
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    clearTimeout(this.reconnectTimer);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.setStatus('disconnected');
  }

  public subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  public onStatusChange(listener: (status: WebSocketConnectionStatus) => void): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  public getStatus(): WebSocketConnectionStatus {
    return this.status;
  }

  private setStatus(status: WebSocketConnectionStatus): void {
    this.status = status;
    this.statusListeners.forEach((listener) => listener(status));
  }
}

export const wsService = new NepseWebSocketService();
