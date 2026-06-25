import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { RecommendationFlow, type QuotaInfo } from "../components/recommendation/RecommendationFlow";
import { useAuthStore } from "../stores/authStore";

export function AuthChatPage() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | undefined>();

  useEffect(() => {
    const at = localStorage.getItem("access_token");
    if (!at) return;
    fetch("/api/v1/recommend/quota", {
      headers: { Authorization: `Bearer ${at}` },
    })
      .then((r) => r.json())
      .then(setQuotaInfo)
      .catch(() => {});
  }, []);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated && !localStorage.getItem("access_token")) {
      navigate("/login");
    }
  }, [isAuthenticated, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <RecommendationFlow
      variant="auth"
      quotaInfo={quotaInfo}
      getSSEUrl={({ cardIds, freeText, sceneTag, intent, environment, diversity, sessionMode }) => {
        const params = new URLSearchParams();
        if (cardIds.length > 0) params.set("card_ids", cardIds.join(","));
        else params.set("card_ids", "");
        if (freeText) params.set("text", freeText);
        if (sceneTag) params.set("scene", sceneTag);
        if (intent && intent !== "self_use") params.set("intent", intent);
        // Environment (FR-2.8)
        if (environment.season) params.set("season", environment.season);
        if (environment.time_of_day) params.set("time_of_day", environment.time_of_day);
        if (environment.weather_code !== null) params.set("weather_code", String(environment.weather_code));
        if (environment.temperature !== null) params.set("temperature", String(environment.temperature));
        // Diversity (FR-3.8)
        if (diversity > 0) params.set("diversity", String(diversity));
        // Session mode (FR-1.5)
        if (sessionMode && sessionMode !== "context") params.set("session_mode", sessionMode);
        // Pass token as query param for EventSource (cannot send custom headers)
        const at = localStorage.getItem("access_token");
        if (at) params.set("token", at);
        return `/api/v1/recommend/sessions?${params.toString()}`;
      }}
      onLogout={handleLogout}
    />
  );
}
