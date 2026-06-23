import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ShareCard } from "../components/share/ShareCard";
import { getShareDetail, type SharePayloadData } from "../lib/apiClient";

export function SharePage() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [payload, setPayload] = useState<SharePayloadData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getShareDetail(id)
      .then((data) => {
        setPayload(data.payload);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.message?.includes("410") || err?.message?.includes("expired")) {
          setError("This share link has expired — start your own experience!");
        } else {
          setError("Share link not found");
        }
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-dvh bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-stone-400">Loading shared recommendation...</p>
        </div>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="min-h-dvh bg-stone-50 flex items-center justify-center p-6">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card p-8 max-w-md text-center">
          <p className="text-2xl mb-3">🔗</p>
          <h2 className="text-lg font-semibold text-stone-700 mb-2">{error || "Share link not available"}</h2>
          <Link to="/" className="inline-block mt-4 text-sm text-stone-600 hover:text-stone-800 bg-stone-100 rounded-full px-5 py-2.5 transition-colors">
            Start your own experience →
          </Link>
        </motion.div>
      </div>
    );
  }

  return <ShareCard payload={payload} />;
}
