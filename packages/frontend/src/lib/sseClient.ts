type SSEStatus = "idle" | "connecting" | "active" | "retrying" | "disconnected";

type SSEMessageHandler = (type: string, data: Record<string, unknown>) => boolean | void;

const BACKOFF_SCHEDULE = [1000, 2000, 4000, 4000, 4000];
const HEARTBEAT_TIMEOUT = 30000;

export function createSSEConnection(
  url: string,
  onEvent: SSEMessageHandler,
  onStatus: (status: SSEStatus) => void,
): () => void {
  let es: EventSource | null = null;
  let retryIndex = 0;
  let heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  const STREAM_TERMINAL_EVENTS = new Set(["gen.complete", "gen.error"]);

  const knownTypes = [
    "chat.ack", "chat.emotion", "chat.intent", "chat.error",
    "gen.start", "gen.skeleton", "gen.detail", "gen.copy",
    "gen.complete", "gen.error",
    "gate.check", "gate.ask", "gate.wait",
    "refine.start", "refine.result", "refine.gate", "refine.fallback",
    "safety.ok", "safety.warn", "safety.crisis", "safety.block",
    "lifecycle.session", "lifecycle.resume",
    "system.heartbeat", "system.notification", "system.error",
  ];

  function resetHeartbeat() {
    if (heartbeatTimer) clearTimeout(heartbeatTimer);
    heartbeatTimer = setTimeout(() => {
      onStatus("disconnected");
      es?.close();
      maybeReconnect();
    }, HEARTBEAT_TIMEOUT);
  }

  function connect() {
    if (stopped) return;

    onStatus(retryIndex === 0 ? "connecting" : "retrying");
    es = new EventSource(url);

    // Register handlers for all known event types
    for (const evtType of knownTypes) {
      es.addEventListener(evtType, (event: MessageEvent) => {
        resetHeartbeat();
        onStatus("active");
        retryIndex = 0; // Reset on successful message
        try {
          const data = JSON.parse(event.data);
          const shouldStop = onEvent(evtType, data);
          // Terminal events: close cleanly without triggering reconnect
          if (shouldStop || STREAM_TERMINAL_EVENTS.has(evtType)) {
            stopped = true;
            es?.close();
          }
        } catch {
          onEvent(evtType, { raw: event.data });
        }
      });
    }

    // Generic message handler for unregistered events
    es.onmessage = (event: MessageEvent) => {
      resetHeartbeat();
      try {
        const data = JSON.parse(event.data);
        onEvent(data.type || "unknown", data);
      } catch {
        // Ignore unparseable messages
      }
    };

    es.onerror = () => {
      if (heartbeatTimer) clearTimeout(heartbeatTimer);
      onStatus("disconnected");
      es?.close();
      maybeReconnect();
    };

    es.onopen = () => {
      onStatus("active");
      resetHeartbeat();
    };
  }

  function maybeReconnect() {
    if (stopped) return;
    if (retryIndex >= BACKOFF_SCHEDULE.length) {
      // Max retries exceeded
      retryIndex = 0;
      // Wait 30s then restart the schedule
      setTimeout(connect, 30000);
      return;
    }
    const delay = BACKOFF_SCHEDULE[retryIndex];
    retryIndex++;
    setTimeout(connect, delay);
  }

  connect();

  return () => {
    stopped = true;
    if (heartbeatTimer) clearTimeout(heartbeatTimer);
    es?.close();
  };
}
