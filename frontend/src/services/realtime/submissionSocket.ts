export interface SubmissionUpdateMessage {
  type: 'submission_update';
  submission_id: number;
  user_id?: number;
  status: 'queued' | 'running' | 'finished';
  verdict: string | null;
  runtime: number | null;
  memory: number | null;
  error_output: string | null;
}

interface SubmissionSocketClientOptions {
  token: string;
  submissionId: number;
  pingIntervalMs?: number;
  baseReconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
  maxReconnectAttempts?: number;
  onUpdate: (message: SubmissionUpdateMessage) => void;
  onTerminalDisconnect?: () => void;
}

function buildSocketUrl(token: string): string {
  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProto}//${window.location.host}/api/ws/submissions/${token}`;
}

export class SubmissionSocketClient {
  private readonly token: string;
  private readonly submissionId: number;
  private readonly pingIntervalMs: number;
  private readonly baseReconnectDelayMs: number;
  private readonly maxReconnectDelayMs: number;
  private readonly maxReconnectAttempts: number;
  private readonly onUpdate: (message: SubmissionUpdateMessage) => void;
  private readonly onTerminalDisconnect?: () => void;

  private ws: WebSocket | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private reconnectAttempts = 0;

  constructor(options: SubmissionSocketClientOptions) {
    this.token = options.token;
    this.submissionId = options.submissionId;
    this.pingIntervalMs = options.pingIntervalMs ?? 15000;
    this.baseReconnectDelayMs = options.baseReconnectDelayMs ?? 500;
    this.maxReconnectDelayMs = options.maxReconnectDelayMs ?? 5000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
    this.onUpdate = options.onUpdate;
    this.onTerminalDisconnect = options.onTerminalDisconnect;
  }

  start(): void {
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    this.clearReconnect();
    this.stopHeartbeat();

    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore close errors
      }
      this.ws = null;
    }
  }

  private connect(): void {
    if (this.stopped || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    let ws: WebSocket;
    try {
      ws = new WebSocket(buildSocketUrl(this.token));
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws = ws;

    ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.sendJson({ action: 'subscribe', submission_id: this.submissionId });
    };

    ws.onmessage = (event) => {
      let message: unknown;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }

      if (!message || typeof message !== 'object') {
        return;
      }

      const typed = message as Partial<SubmissionUpdateMessage> & { type?: string; submission_id?: unknown };
      if (typed.type !== 'submission_update' || typed.submission_id !== this.submissionId) {
        return;
      }

      this.onUpdate({
        type: 'submission_update',
        submission_id: this.submissionId,
        user_id: typeof typed.user_id === 'number' ? typed.user_id : undefined,
        status: (typed.status as SubmissionUpdateMessage['status']) ?? 'queued',
        verdict: (typed.verdict as string | null) ?? null,
        runtime: (typed.runtime as number | null) ?? null,
        memory: (typed.memory as number | null) ?? null,
        error_output: (typed.error_output as string | null) ?? null,
      });
    };

    ws.onclose = () => {
      this.stopHeartbeat();
      if (this.stopped) return;
      this.scheduleReconnect();
    };

    ws.onerror = () => {
      // `onclose` will handle reconnect logic.
    };
  }

  private sendJson(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      this.ws.send(JSON.stringify(payload));
    } catch {
      // ignore send failures, reconnect flow will handle disconnect
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.pingTimer = setInterval(() => {
      this.sendJson({ action: 'ping' });
    }, this.pingIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private clearReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped) {
      return;
    }

    this.clearReconnect();
    this.reconnectAttempts += 1;

    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      this.stop();
      this.onTerminalDisconnect?.();
      return;
    }

    const backoff = this.baseReconnectDelayMs * (2 ** (this.reconnectAttempts - 1));
    const delay = Math.min(backoff, this.maxReconnectDelayMs);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }
}
