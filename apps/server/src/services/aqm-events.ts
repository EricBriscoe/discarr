import type { Response } from 'express';

type AqmEvent = {
  type: string;
  runId?: string;
  ts?: string;
  data?: any;
};

class AqmEvents {
  private clients = new Set<Response>();
  private keepaliveTimers = new Map<Response, NodeJS.Timeout>();

  addClient(res: Response) {
    this.clients.add(res);
    try { res.write(`: connected\n\n`); } catch {}
    const timer = setInterval(() => {
      try {
        const payload = JSON.stringify({ type: 'ping', ts: new Date().toISOString() });
        res.write(`event: aqm\n`);
        res.write(`data: ${payload}\n\n`);
      } catch {
        this.removeClient(res);
      }
    }, 25000);
    this.keepaliveTimers.set(res, timer);
  }

  removeClient(res: Response) {
    if (this.keepaliveTimers.has(res)) {
      clearInterval(this.keepaliveTimers.get(res)!);
      this.keepaliveTimers.delete(res);
    }
    try { res.end(); } catch {}
    this.clients.delete(res);
  }

  send(event: AqmEvent) {
    const payload = JSON.stringify({ ...event, ts: event.ts || new Date().toISOString() });
    for (const res of this.clients) {
      try {
        res.write(`event: aqm\n`);
        res.write(`data: ${payload}\n\n`);
      } catch {
        this.removeClient(res);
      }
    }
  }
}

export const aqmEvents = new AqmEvents();

