import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-dvh bg-stone-50 flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-10 text-center max-w-sm"
      >
        <span className="text-5xl">🔮</span>
        <h1 className="text-2xl font-light text-stone-800 mt-4">Page Not Found</h1>
        <p className="text-stone-500 mt-2 text-sm leading-relaxed">
          This scent doesn't exist yet. Let's find your way back.
        </p>
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate("/")}
          className="mt-6"
        >
          Back Home
        </Button>
      </motion.div>
    </div>
  );
}
