import { useEffect, useRef, useCallback } from "react";
import type { WSMessage } from "@/lib/types";

const RECONNECT_DELAYS = [2000, 5000, 10000, 30000];
const PING_INTERVAL = 30000;

export function useWebSocket(
  jobId: string,
  onMessage: (msg: WSMessage) => void,
  enabled: boolean = true
) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const pingIntervalRef = useRef<number | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!jobId || !enabled) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const url = `${protocol}://${host}/ws/jobs/${jobId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      // Start ping
      pingIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        if (msg.type !== "pong") {
          onMessageRef.current(msg);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      // Retry with backoff
      if (enabled && retryCountRef.current < RECONNECT_DELAYS.length) {
        const delay = RECONNECT_DELAYS[retryCountRef.current];
        retryCountRef.current++;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [jobId, enabled]);

  useEffect(() => {
    connect();
    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);
}
