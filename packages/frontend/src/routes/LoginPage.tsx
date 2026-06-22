import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";
import { useAuthStore } from "../stores/authStore";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/app");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center">
          <a href="/" className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Home
          </a>
        </div>
      </nav>
      <div className="flex-1 flex items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="max-w-sm w-full space-y-6">
          <div>
            <h1 className="text-2xl font-semibold text-stone-800">Welcome back</h1>
            <p className="text-sm text-stone-500 mt-1">Sign in to continue your scent journey</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1.5">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com" required
                className="w-full rounded-xl glass-card px-4 py-3 text-sm text-stone-800
                           placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1.5">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••" required
                className="w-full rounded-xl glass-card px-4 py-3 text-sm text-stone-800
                           placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-400" />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button variant="primary" disabled={loading} className="w-full">
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
          <p className="text-sm text-stone-400 text-center">
            No account? <Link to="/register" className="text-stone-600 hover:text-stone-800 underline">Register →</Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
