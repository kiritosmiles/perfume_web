import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/Button";
import { getPerfumerQueue, type PerfumerQueueItem } from "../lib/apiClient";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  accepted: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-stone-100 text-stone-500",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  accepted: "In Production",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function MyCardsPage() {
  const navigate = useNavigate();
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  const [queue, setQueue] = useState<PerfumerQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPerfumerQueue()
      .then((res) => {
        setQueue(res.items);
        setLoading(false);
      })
      .catch((e) => {
        // Backend may not have this endpoint yet — fail gracefully
        setFetchError(e?.message || null);
        setQueue([]);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!isAuth) navigate("/login", { replace: true });
  }, [isAuth, navigate]);

  if (!isAuth) return null;

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/app")} className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Back
          </button>
          <span className="text-sm font-medium text-stone-700">My Cards</span>
          <div className="w-12" />
        </div>
      </nav>

      <div className="max-w-md mx-auto px-4 py-8">
        {loading ? (
          <div className="text-center py-16">
            <div className="w-6 h-6 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin mx-auto" />
          </div>
        ) : queue.length === 0 ? (
          <div className="text-center py-16">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="glass-card p-8 space-y-4"
            >
              <span className="text-4xl">🪄</span>
              <h2 className="text-lg font-semibold text-stone-700">No cards in production</h2>
              <p className="text-sm text-stone-500 leading-relaxed">
                When you find a fragrance you love, you can request a physical perfume card
                crafted by our perfumer Helen Yee.
              </p>
              <Button variant="primary" size="sm" onClick={() => navigate("/app")}>
                Try a recommendation →
              </Button>
            </motion.div>
          </div>
        ) : (
          <div className="space-y-3">
            {queue.map((item) => (
              <motion.div key={item.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="glass-card p-4 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-stone-700">{item.perfume_name}</p>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_STYLE[item.status] || STATUS_STYLE.pending}`}>
                    {STATUS_LABEL[item.status] || item.status}
                  </span>
                </div>
                <p className="text-xs text-stone-500">{item.notes}</p>
                <p className="text-[10px] text-stone-400">Submitted: {item.created_at}</p>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

