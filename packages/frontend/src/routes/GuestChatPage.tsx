import { RecommendationFlow } from "../components/recommendation/RecommendationFlow";

export function GuestChatPage() {
  return (
    <RecommendationFlow
      variant="guest"
      getSSEUrl={({ cardIds, freeText, sceneTag }) => {
        const params = new URLSearchParams();
        if (cardIds.length > 0) params.set("card_ids", cardIds.join(","));
        else params.set("card_ids", "");
        if (freeText) params.set("text", freeText);
        if (sceneTag) params.set("scene", sceneTag);
        return `/api/v1/guest/sessions?${params.toString()}`;
      }}
    />
  );
}
