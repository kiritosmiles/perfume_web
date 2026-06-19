import { Routes, Route } from "react-router-dom";
import { LandingPage } from "./routes/LandingPage";
import { GuestChatPage } from "./routes/GuestChatPage";
import { FallbackPage } from "./routes/FallbackPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/guest" element={<GuestChatPage />} />
      <Route path="/fallback" element={<FallbackPage />} />
      <Route path="*" element={<FallbackPage />} />
    </Routes>
  );
}
