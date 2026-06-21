import { Routes, Route } from "react-router-dom";
import { LandingPage } from "./routes/LandingPage";
import { GuestChatPage } from "./routes/GuestChatPage";
import { FallbackPage } from "./routes/FallbackPage";
import { NotFoundPage } from "./routes/NotFoundPage";
import { SettingsPage } from "./routes/SettingsPage";
import { SharePage } from "./routes/SharePage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/guest" element={<GuestChatPage />} />
      <Route path="/fallback" element={<FallbackPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/s/:id" element={<SharePage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
