import { Routes, Route } from "react-router-dom";
import { LandingPage } from "./routes/LandingPage";
import { GuestChatPage } from "./routes/GuestChatPage";
import { FallbackPage } from "./routes/FallbackPage";
import { NotFoundPage } from "./routes/NotFoundPage";
import { SettingsPage } from "./routes/SettingsPage";
import { SharePage } from "./routes/SharePage";
import { LoginPage } from "./routes/LoginPage";
import { RegisterPage } from "./routes/RegisterPage";
import { AuthChatPage } from "./routes/AuthChatPage";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/guest" element={<GuestChatPage />} />
      <Route path="/fallback" element={<FallbackPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/s/:id" element={<SharePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/app" element={<ProtectedRoute><AuthChatPage /></ProtectedRoute>} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
