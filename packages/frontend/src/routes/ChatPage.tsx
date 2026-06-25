import { Link } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

export function ChatPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // Read query params for intent/scene shortcuts
  const params = new URLSearchParams(window.location.search);
  const intentParam = params.get("intent");
  const sceneParam = params.get("scene");

  if (isAuthenticated) {
    // Build redirect with query params preserved
    const searchParams = new URLSearchParams();
    if (intentParam) searchParams.set("intent", intentParam);
    if (sceneParam) searchParams.set("scene", sceneParam);
    const qs = searchParams.toString();
    window.location.href = `/app${qs ? `?${qs}` : ""}`;
    return null;
  }

  // Guest: redirect to /guest with query params
  const searchParams = new URLSearchParams();
  if (intentParam) searchParams.set("intent", intentParam);
  if (sceneParam) searchParams.set("scene", sceneParam);
  const qs = searchParams.toString();
  window.location.href = `/guest${qs ? `?${qs}` : ""}`;
  return null;
}
