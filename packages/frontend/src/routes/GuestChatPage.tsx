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
import { useSSE } from "../hooks/useSSE";
import { useSessionStore } from "../stores/sessionStore";
import { useGenerationStore } from "../stores/generationStore";

export function GuestChatPage() {
  const [cardIds, setCardIds] = useState<string[]>([]);
  const [sceneTag, setSceneTag] = useState<string>("");
  const [sseUrl, setSseUrl] = useState<string | null>(null);

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

  const handleStart = () => {
    if (cardIds.length === 0) return;
    const params = new URLSearchParams();
    params.set("card_ids", cardIds.join(","));
    if (sceneTag) params.set("scene", sceneTag);
    setSseUrl(`/api/v1/guest/sessions?${params.toString()}`);
  };

  const handleReset = () => {
    close();
    setSseUrl(null);
    setCardIds([]);
    setSceneTag("");
    useSessionStore.getState().reset();
    useGenerationStore.getState().reset();
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
            className="max-w-md mx-auto pt-8 space-y-8"
          >
            <EmotionCardPicker
              selectedIds={cardIds}
              onToggle={handleToggleCard}
              maxSelection={2}
            />
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
              onCorrect={() => {
                close();
                setSseUrl(null);
                setCardIds([]);
              }}
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
            disabled={cardIds.length === 0}
            onClick={handleStart}
            className="w-full"
          >
            Start Exploring
          </Button>
        ) : generationPhase === "complete" ? (
          <Button
            variant="glass"
            onClick={handleReset}
            className="w-full"
          >
            Start New Session
          </Button>
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
