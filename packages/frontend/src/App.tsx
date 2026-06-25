import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { LandingPage } from "./routes/LandingPage";
import { GuestChatPage } from "./routes/GuestChatPage";
import { ChatPage } from "./routes/ChatPage";
import { FallbackPage } from "./routes/FallbackPage";
import { NotFoundPage } from "./routes/NotFoundPage";
import { SettingsPage } from "./routes/SettingsPage";
import { SharePage } from "./routes/SharePage";
import { LoginPage } from "./routes/LoginPage";
import { RegisterPage } from "./routes/RegisterPage";
import { AuthChatPage } from "./routes/AuthChatPage";
import { OnboardingPage } from "./routes/OnboardingPage";
import { SafetyProfilePage } from "./routes/SafetyProfilePage";
import { MoodJournalPage } from "./routes/MoodJournalPage";
import { HistoryListPage } from "./routes/HistoryListPage";
import { HistoryDetailPage } from "./routes/HistoryDetailPage";
import { MyCardsPage } from "./routes/MyCardsPage";
import { CrisisResourcesPage } from "./routes/CrisisResourcesPage";
import { PrivacyPage } from "./routes/PrivacyPage";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { MemoryPage } from "./routes/MemoryPage";
import { ProfilePage } from "./routes/ProfilePage";
import { useAuthStore } from "./stores/authStore";

export function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="/guest" element={<GuestChatPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/s/:id" element={<SharePage />} />
      <Route path="/fallback" element={<FallbackPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/crisis-resources" element={<CrisisResourcesPage />} />

      {/* Semi-public (views data but does not require login for guest access) */}
      <Route path="/memory" element={<MemoryPage />} />
      <Route path="/history" element={<HistoryListPage />} />
      <Route path="/history/:sessionId" element={<HistoryDetailPage />} />

      {/* Protected (auth required) */}
      <Route path="/app" element={<ProtectedRoute><AuthChatPage /></ProtectedRoute>} />
      <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/profile/safety" element={<ProtectedRoute><SafetyProfilePage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/mood-journal" element={<ProtectedRoute><MoodJournalPage /></ProtectedRoute>} />
      <Route path="/my-cards" element={<ProtectedRoute><MyCardsPage /></ProtectedRoute>} />

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
