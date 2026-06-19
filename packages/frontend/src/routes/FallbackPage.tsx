import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";

export function FallbackPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-dvh flex items-center justify-center bg-stone-50 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-12 text-center max-w-md w-full"
      >
        <span className="text-6xl">🍃</span>
        <h2 className="mt-4 text-xl font-light text-stone-700">
          Come back later
        </h2>
        <p className="mt-2 text-stone-400 text-sm leading-relaxed">
          We're preparing something special for you.
          <br />
          This feature will be available soon.
        </p>
        <Button
          variant="glass"
          onClick={() => navigate("/")}
          className="mt-6"
        >
          Go Home
        </Button>
      </motion.div>
    </div>
  );
}
