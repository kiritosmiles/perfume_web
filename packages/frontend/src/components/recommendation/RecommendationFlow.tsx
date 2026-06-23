import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { EmotionCardPicker } from "../emotion/EmotionCardPicker";
import { EmotionConfirmation } from "../emotion/EmotionConfirmation";
import { SceneTagChips } from "../chat/SceneTagChips";
import { IntentSelector } from "../chat/IntentSelector";
import { ChatBody } from "../chat/ChatBody";
import { ChatInput } from "../chat/ChatInput";
import { ThinkingIndicator } from "../chat/ThinkingIndicator";
import { FragranceCard } from "../fragrance/FragranceCard";
import { Button } from "../ui/Button";
import { NetworkStatusBar } from "../ui/NetworkStatusBar";
import { NoteCard } from "../notes/NoteCard";
import { ExportButton } from "../notes/ExportButton";
import { GateQuestionBanner } from "../chat/GateQuestionBanner";
import { useSSE } from "../../hooks/useSSE";
import { useImplicitTracking } from "../../hooks/useImplicitTracking";
import { useSessionStore } from "../../stores/sessionStore";
import { useGenerationStore } from "../../stores/generationStore";
import { createShareLink } from "../../lib/apiClient";
import { CrisisOverlay } from "../safety/CrisisOverlay";
import { RefinementChips } from "../refinement/RefinementChips";

export interface QuotaInfo {
  sessions?: { used: number; max: number; remaining: number };
  generations?: { used: number; max: number; remaining: number };
  deep?: { used: number; max: number; remaining: number };
}

interface RecommendationFlowProps {
  variant: "guest" | "auth";
  getSSEUrl: (params: {
    cardIds: string[];
    freeText: string;
    sceneTag: string;
    intent: "self_use" | "gift" | "explore";
  }) => string | null;
  quotaInfo?: QuotaInfo;
  onQuotaExhausted?: () => void;
  onLogout?: () => void;
}

export function RecommendationFlow({
  variant: _variant,
  getSSEUrl,
  quotaInfo,
  onQuotaExhausted,
  onLogout,
}: RecommendationFlowProps) {
  const [inputMode, setInputMode] = useState<"cards" | "text">("cards");
  const [cardIds, setCardIds] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [sceneTag, setSceneTag] = useState<string>("");
  const [intent, setIntent] = useState<"self_use" | "gift" | "explore">("self_use");
  const [sseUrl, setSseUrl] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  const emotion = useSessionStore((s) => s.emotion);
  const sseStatus = useSessionStore((s) => s.sseStatus);
  const crisis = useSessionStore((s) => s.crisis);
  const generationPhase = useGenerationStore((s) => s.phase);
  const cards = useGenerationStore((s) => s.cards);
  const generationError = useGenerationStore((s) => s.error);
  const gate = useSessionStore((s) => s.gate);

  const navigate = useNavigate();
  const { close } = useSSE({ url: sseUrl });

  // Implicit feedback tracking (dwell, share, refine events)
  const { track } = useImplicitTracking();

  const noteRef = useRef<HTMLDivElement>(null);
  const noteFilename = `perfume-note-${new Date().toISOString().slice(0, 10)}.png`;

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
    const url = getSSEUrl({ cardIds, freeText: freeText.trim(), sceneTag, intent });
    if (!url) {
      onQuotaExhausted?.();
      return;
    }
    // Append allergens from localStorage if configured
    const allergens = localStorage.getItem("perfume_allergens") || "";
    const finalUrl = allergens ? `${url}&allergens=${encodeURIComponent(allergens)}` : url;
    setSseUrl(finalUrl);
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
          rank: c.rank,
          name: c.name,
          brand: c.brand,
          notes_combination: c.notes_combination,
          match_score: c.match_score,
          copy_text: c.copy_text,
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
      track("share_clicked", { card_count: cards.length });
    } catch {
      // Share failed silently
    } finally {
      setSharing(false);
    }
  };

  const handleRefine = (key: string) => {
    close();
    setSseUrl(null);
    // Rebuild the same URL but append the refine param
    const baseUrl = getSSEUrl({ cardIds, freeText: freeText.trim(), sceneTag, intent });
    if (!baseUrl) return;
    const allergens = localStorage.getItem("perfume_allergens") || "";
    let refineUrl = `${baseUrl}&refine=${encodeURIComponent(key)}`;
    if (allergens) refineUrl += `&allergens=${encodeURIComponent(allergens)}`;
    track("refine_used", { keyword: key });
    setSseUrl(refineUrl);
  };

  const handleGateAnswer = (answer: string) => {
    close();
    setSseUrl(null);
    const baseUrl = getSSEUrl({ cardIds, freeText: freeText.trim(), sceneTag, intent });
    if (!baseUrl) return;
    const allergens = localStorage.getItem("perfume_allergens") || "";
    let gateUrl = `${baseUrl}&gate_answer=${encodeURIComponent(answer)}`;
    if (allergens) gateUrl += `&allergens=${encodeURIComponent(allergens)}`;
    setSseUrl(gateUrl);
  };

  const handleGateSkip = () => {
    handleGateAnswer("skip");
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

      {/* Crisis overlay — rendered when safety.crisis/safety.block detected */}
      {crisis?.is_crisis && (
        <CrisisOverlay
          severity={crisis.severity}
          onReset={handleReset}
        />
      )}

      {/* Nav header */}
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button
            onClick={() => {
              if (hasStarted) {
                handleReset();
              } else {
                navigate("/");
              }
            }}
            className="text-stone-500 hover:text-stone-800 transition-colors text-sm"
          >
            {hasStarted ? "← New Session" : "← Home"}
          </button>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${statusDot}`} />
              <span className="text-xs text-stone-400 capitalize">{sseStatus}</span>
            </div>
            {onLogout && (
              <>
                <button
                  onClick={() => navigate("/profile")}
                  className="text-xs text-stone-400 hover:text-stone-600 transition-colors"
                >
                  Profile
                </button>
                <button
                  onClick={onLogout}
                  className="text-xs text-stone-400 hover:text-stone-600 transition-colors"
                >
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Quota info bar (auth only) */}
      {quotaInfo && (
        <div className="max-w-md mx-auto mt-3 flex justify-center gap-4 text-xs text-stone-400">
          <span>
            Sessions: {quotaInfo.sessions?.remaining ?? "—"}/
            {quotaInfo.sessions?.max ?? "—"}
          </span>
          <span>
            Generations: {quotaInfo.generations?.remaining ?? "—"}/
            {quotaInfo.generations?.max ?? "—"}
          </span>
        </div>
      )}

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
                  onClick={() => {
                    setInputMode(mode);
                    setCardIds([]);
                    setFreeText("");
                  }}
                  className={`flex-1 py-2 text-sm font-medium rounded-full transition-all
                    ${
                      inputMode === mode
                        ? "bg-white text-stone-800 shadow-sm"
                        : "text-stone-400 hover:text-stone-600"
                    }`}
                >
                  {mode === "cards"
                    ? "🎭 Pick a Card"
                    : "✍️ Write how you feel"}
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
                Intent
              </p>
              <div className="flex justify-center">
                <IntentSelector
                  value={intent}
                  onChange={setIntent}
                  isGuest={_variant === "guest"}
                />
              </div>
            </div>

            <div>
              <p className="text-xs text-stone-400 text-center mb-3 font-medium uppercase tracking-wider">
                Optional · Scene
              </p>
              <div className="flex justify-center">
                <SceneTagChips
                  selected={[sceneTag]}
                  onToggle={handleToggleScene}
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* Agent Gate: show questions when information is insufficient */}
        {gate && gate.verdict === "insufficient" && gate.questions && (
          <div className="max-w-md mx-auto pt-4">
            <GateQuestionBanner
              questions={gate.questions}
              hint={gate.hint || "你可以回答这些问题，或直接说「先推荐看看」"}
              onSubmit={handleGateAnswer}
              onSkip={handleGateSkip}
            />
          </div>
        )}

        {emotion && hasStarted && !gate?.questions && (
          <div className="max-w-md mx-auto">
            <EmotionConfirmation
              visible={!!emotion.primary_emotion}
              primaryEmotion={emotion.primary_emotion || ""}
              confidence={emotion.confidence || 0}
              onCorrect={handleCorrect}
              onConfirm={() => {}}
              onClarify={handleCorrect}
            />
          </div>
        )}

        {isGenerating && cards.length === 0 && (
          <div className="max-w-md mx-auto">
            <ThinkingIndicator text="Analyzing your emotions..." />
          </div>
        )}

        <div className="w-full px-4">
          {/* Horizontal scroll container for cards */}
          <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory
                          scrollbar-hide -mx-2 px-2">
            {cards.map((card, i) => (
              <div key={card.rank} className="snap-start">
                <FragranceCard
                  card={card}
                  phase={generationPhase}
                  index={i}
                />
              </div>
            ))}

            {generationPhase === "skeleton" && cards.length === 0 && (
              <>
                <FragranceCard card={null} phase="skeleton" index={0} />
                <FragranceCard card={null} phase="skeleton" index={1} />
                <FragranceCard card={null} phase="skeleton" index={2} />
              </>
            )}
          </div>
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
          <div className="space-y-3 w-full">
            {/* Refinement chips */}
            <RefinementChips onSelect={handleRefine} />

            {shareUrl && (
              <div className="glass-card px-3 py-2 text-center text-xs text-green-700">
                Link copied! 📋
              </div>
            )}
            <div className="flex gap-2">
              <ExportButton targetRef={noteRef} filename={noteFilename} />
              <Button
                variant="glass"
                size="sm"
                onClick={handleShare}
                disabled={sharing}
              >
                {sharing ? "Creating link..." : "Share"}
              </Button>
              <Button
                variant="primary"
                onClick={handleReset}
                className="flex-1"
              >
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

      {/* Offscreen note card for PNG export */}
      <div ref={noteRef} className="fixed -left-[9999px] top-0">
        <NoteCard
          cards={cards}
          primaryEmotion={emotion?.primary_emotion || "Unknown"}
          confidence={emotion?.confidence || 0}
          sceneTag={sceneTag || undefined}
          generationId={
            useGenerationStore.getState().generationId || undefined
          }
        />
      </div>
    </div>
  );
}
