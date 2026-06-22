import { useState, useEffect } from "react";
import { RecommendationFlow, type QuotaInfo } from "../components/recommendation/RecommendationFlow";
import { useAuthStore } from "../stores/authStore";

export function AuthChatPage() {
  const logout = useAuthStore((s) => s.logout);
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

  return (
    <RecommendationFlow
      variant="auth"
      quotaInfo={quotaInfo}
      getSSEUrl={({ cardIds, freeText, sceneTag }) => {
        const params = new URLSearchParams();
        if (cardIds.length > 0) params.set("card_ids", cardIds.join(","));
        else params.set("card_ids", "");
        if (freeText) params.set("text", freeText);
        if (sceneTag) params.set("scene", sceneTag);
        return `/api/v1/recommend/sessions?${params.toString()}`;
      }}
    />
  );
}
