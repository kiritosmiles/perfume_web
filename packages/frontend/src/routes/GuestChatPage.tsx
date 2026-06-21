import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { EmotionCardPicker } from "../components/emotion/EmotionCardPicker";
import { EmotionConfirmation } from "../components/emotion/EmotionConfirmation";
import { SceneTagChips } from "../components/chat/SceneTagChips";
import { ChatBody } from "../components/chat/ChatBody";
import { ChatInput } from "../components/chat/ChatInput";
import { ThinkingIndicator } from "../components/chat/ThinkingIndicator";
import { FragranceCard } from "../components/fragrance/FragranceCard";
import { Button } from "../components/ui/Button";
import { NetworkStatusBar } from "../components/ui/NetworkStatusBar";
import { useSSE } from "../hooks/useSSE";
import { useSessionStore } from "../stores/sessionStore";
import { useGenerationStore } from "../stores/generationStore";
import { createShareLink } from "../lib/apiClient";

export function GuestChatPage() {
  const [inputMode, setInputMode] = useState<"cards" | "text">("cards");
  const [cardIds, setCardIds] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [sceneTag, setSceneTag] = useState<string>("");
  const [sseUrl, setSseUrl] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  const emotion = useSessionStore((s) => s.emotion);
  const sseStatus = useSessionStore((s) => s.sseStatus);
  const generationPhase = useGenerationStore((s) => s.phase);
  const cards = useGenerationStore((s) => s.cards);
  const generationError = useGenerationStore((s) => s.error);

  const { close } = useSSE({ url: sseUrl });

  const handleToggleCard = useCallback((id: string) => {
    setCardIds((prev) => {
      if (prev.includes(id)) return prev.filter((c) => c !== id);
      if (prev.length >= 2) return prev;
      return [...prev, id];
    });
  }, []);

  const handleToggleScene = useCallback((id: string) => {
    setSceneTag((prev) => (prev === id ? "" : id));
  }, []);

  const canStart =
    inputMode === "cards" ? cardIds.length > 0 : freeText.trim().length > 0;

  const handleStart = () => {
    if (!canStart) return;
    const params = new URLSearchParams();
    if (inputMode === "cards") {
      params.set("card_ids", cardIds.join(","));
    } else {
      params.set("card_ids", "");
      params.set("text", freeText.trim());
    }
    if (sceneTag) params.set("scene", sceneTag);
    setSseUrl(`/api/v1/guest/sessions?${params.toString()}`);
  };

  const handleReset = () => {
    close();
    setSseUrl(null);
    setCardIds([]);
    setFreeText("");
    setSceneTag("");
    useSessionStore.getState().reset();
    useGenerationStore.getState().reset();
  };

  const handleCorrect = () => {
    close();
    setSseUrl(null);
    setCardIds([]);
    setFreeText("");
  };

  const handleShare = async () => {
    if (cards.length === 0 || !emotion) return;
    setSharing(true);
    try {
      const res = await createShareLink({
        recommendations: cards.map((c) => ({
          rank: c.rank, name: c.name, brand: c.brand,
          notes_combination: c.notes_combination,
          match_score: c.match_score, copy_text: c.copy_text,
        })),
        emotion: {
          primary_emotion: emotion.primary_emotion,
          confidence: emotion.confidence,
          emotion_vector: emotion.emotion_vector,
        },
        scene_tag: sceneTag || null,
        generation_id: useGenerationStore.getState().generationId,
      });
      const fullUrl = `${window.location.origin}${res.share_url}`;
      setShareUrl(fullUrl);
      await navigator.clipboard.writeText(fullUrl);
    } catch {
      // Share failed silently
    } finally {
      setSharing(false);
    }
  };

  const isGenerating =
    generationPhase !== "idle" &&
    generationPhase !== "complete" &&
    generationPhase !== "error";
  const hasStarted = sseUrl !== null;

  const statusDot = {
    idle: "bg-stone-300",
    connecting: "bg-amber-400 animate-pulse",
    active: "bg-green-500",
    retrying: "bg-amber-500 animate-pulse",
    disconnected: "bg-red-500",
  }[sseStatus];

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col">
      {/* Network status bar — thin top strip for connection state */}
      <NetworkStatusBar />

      {/* Nav header */}
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button
            onClick={handleReset}
            className="text-stone-500 hover:text-stone-800 transition-colors text-sm"
          >
            {hasStarted ? "← New Session" : "← Home"}
          </button>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${statusDot}`} />
            <span className="text-xs text-stone-400 capitalize">{sseStatus}</span>
          </div>
        </div>
      </nav>

      {/* Chat body */}
      <ChatBody>
        {!hasStarted && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-md mx-auto pt-8 space-y-6"
          >
            {/* Mode toggle */}
            <div className="flex rounded-full bg-stone-200/50 p-0.5">
              {(["cards", "text"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => { setInputMode(mode); setCardIds([]); setFreeText(""); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-full transition-all
                    ${inputMode === mode
                      ? "bg-white text-stone-800 shadow-sm"
                      : "text-stone-400 hover:text-stone-600"
                    }`}
                >
                  {mode === "cards" ? "🎭 Pick a Card" : "✍️ Write how you feel"}
                </button>
              ))}
            </div>

            {inputMode === "cards" ? (
              <EmotionCardPicker
                selectedIds={cardIds}
                onToggle={handleToggleCard}
                maxSelection={2}
              />
            ) : (
              <div className="space-y-2">
                <textarea
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  placeholder="Describe how you're feeling right now..."
                  rows={3}
                  maxLength={300}
                  className="w-full resize-none rounded-xl glass-card px-4 py-3 text-sm
                             text-stone-800 placeholder-stone-400
                             focus:outline-none focus:ring-2 focus:ring-stone-400
                             transition-shadow"
                />
                <p className="text-xs text-stone-400 text-right">
                  {freeText.length}/300
                </p>
              </div>
            )}

            <div>
              <p className="text-xs text-stone-400 text-center mb-3 font-medium uppercase tracking-wider">
                Optional · Scene
              </p>
              <div className="flex justify-center">
                <SceneTagChips selected={[sceneTag]} onToggle={handleToggleScene} />
              </div>
            </div>
          </motion.div>
        )}

        {emotion && hasStarted && (
          <div className="max-w-md mx-auto">
            <EmotionConfirmation
              visible={!!emotion.primary_emotion}
              primaryEmotion={emotion.primary_emotion || ""}
              confidence={emotion.confidence || 0}
              onCorrect={handleCorrect}
            />
          </div>
        )}

        {isGenerating && cards.length === 0 && (
          <div className="max-w-md mx-auto">
            <ThinkingIndicator text="Analyzing your emotions..." />
          </div>
        )}

        <div className="max-w-md mx-auto space-y-4">
          {cards.map((card, i) => (
            <FragranceCard
              key={card.rank}
              card={card}
              phase={generationPhase}
              index={i}
            />
          ))}

          {generationPhase === "skeleton" && cards.length === 0 && (
            <>
              <FragranceCard card={null} phase="skeleton" index={0} />
              <FragranceCard card={null} phase="skeleton" index={1} />
              <FragranceCard card={null} phase="skeleton" index={2} />
            </>
          )}
        </div>

        {generationError && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-md mx-auto glass-card p-5 text-center"
          >
            <p className="text-stone-600">{generationError.user_message}</p>
            <Button
              variant="glass"
              size="sm"
              onClick={handleReset}
              className="mt-3"
            >
              Try Again
            </Button>
          </motion.div>
        )}
      </ChatBody>

      {/* Input bar */}
      <ChatInput disabled={isGenerating}>
        {!hasStarted ? (
          <Button
            variant="primary"
            disabled={!canStart}
            onClick={handleStart}
            className="w-full"
          >
            Start Exploring
          </Button>
        ) : generationPhase === "complete" ? (
          <div className="space-y-2 w-full">
            {shareUrl && (
              <div className="glass-card px-3 py-2 text-center text-xs text-green-700">
                Link copied! 📋
              </div>
            )}
            <div className="flex gap-2">
              <Button variant="glass" size="sm" onClick={handleShare} disabled={sharing}>
                {sharing ? "Creating link..." : "Share"}
              </Button>
              <Button variant="primary" onClick={handleReset} className="flex-1">
                New Session
              </Button>
            </div>
          </div>
        ) : generationPhase === "error" ? (
          <Button
            variant="primary"
            onClick={handleReset}
            className="w-full"
          >
            Try Again
          </Button>
        ) : null}
      </ChatInput>
    </div>
  );
}
