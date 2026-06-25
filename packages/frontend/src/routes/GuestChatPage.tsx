import { RecommendationFlow } from "../components/recommendation/RecommendationFlow";
import { getBrowserId } from "../lib/apiClient";

export function GuestChatPage() {
  return (
    <RecommendationFlow
      variant="guest"
      getSSEUrl={({ cardIds, freeText, sceneTag, intent, environment, diversity, sessionMode }) => {
        const params = new URLSearchParams();
        if (cardIds.length > 0) params.set("card_ids", cardIds.join(","));
        else params.set("card_ids", "");
        if (freeText) params.set("text", freeText);
        if (sceneTag) params.set("scene", sceneTag);
        if (intent && intent !== "self_use") params.set("intent", intent);
        const browserId = getBrowserId();
        if (browserId) params.set("browser_id", browserId);
        // Environment (FR-2.8)
        if (environment.season) params.set("season", environment.season);
        if (environment.time_of_day) params.set("time_of_day", environment.time_of_day);
        if (environment.weather_code !== null) params.set("weather_code", String(environment.weather_code));
        if (environment.temperature !== null) params.set("temperature", String(environment.temperature));
        // Diversity (FR-3.8)
        if (diversity > 0) params.set("diversity", String(diversity));
        // Session mode (FR-1.5)
        if (sessionMode && sessionMode !== "context") params.set("session_mode", sessionMode);
        return `/api/v1/guest/sessions?${params.toString()}`;
      }}
    />
  );
}
