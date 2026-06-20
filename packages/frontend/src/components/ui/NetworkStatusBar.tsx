import { motion, AnimatePresence } from "framer-motion";
import { useSessionStore } from "../../stores/sessionStore";

type StatusLabel = "connected" | "reconnecting" | "disconnected" | "idle";

const STATUS_COPY: Record<StatusLabel, { text: string; bg: string }> = {
  idle:       { text: "", bg: "bg-transparent" },
  connected:   { text: "Connected", bg: "bg-green-500" },
  reconnecting: { text: "Reconnecting…", bg: "bg-amber-500" },
  disconnected: { text: "Connection lost. Retrying…", bg: "bg-red-500" },
};

function sseToBar(sseStatus: string): StatusLabel {
  if (sseStatus === "active") return "connected";
  if (sseStatus === "retrying") return "reconnecting";
  if (sseStatus === "disconnected") return "disconnected";
  return "idle";
}

export function NetworkStatusBar() {
  const sseStatus = useSessionStore((s) => s.sseStatus);
  const status = sseToBar(sseStatus);

  return (
    <AnimatePresence>
      {status !== "idle" && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 24, opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className={`${STATUS_COPY[status].bg} flex items-center justify-center
                      overflow-hidden text-xs text-white font-medium`}
        >
          {STATUS_COPY[status].text}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
