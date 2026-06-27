import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { EmotionCardPicker } from "../emotion/EmotionCardPicker";
import { EmotionConfirmation } from "../emotion/EmotionConfirmation";
import { SceneTagChips } from "../chat/SceneTagChips";
import { IntentSelector } from "../chat/IntentSelector";
import { SessionModeSelector } from "../chat/SessionModeSelector";
import type { SessionMode } from "../chat/SessionModeSelector";
import { ChatBody } from "../chat/ChatBody";
import { ChatInput } from "../chat/ChatInput";
import { ThinkingIndicator } from "../chat/ThinkingIndicator";
import { KnowledgeCardOverlay } from "../chat/KnowledgeCardOverlay";
import { FragranceCard } from "../fragrance/FragranceCard";
import { Button } from "../ui/Button";
import { NetworkStatusBar } from "../ui/NetworkStatusBar";
import { NoteCard } from "../notes/NoteCard";
import { ExportButton } from "../notes/ExportButton";
import { GateQuestionBanner } from "../chat/GateQuestionBanner";
import { useSSE } from "../../hooks/useSSE";
import { useEnvironment, formatEnvironmentLabel, type EnvironmentData } from "../../hooks/useEnvironment";
import { useImplicitTracking } from "../../hooks/useImplicitTracking";
import { useSessionStore } from "../../stores/sessionStore";
import { useGenerationStore } from "../../stores/generationStore";
import { createShareLink } from "../../lib/apiClient";
import { CrisisOverlay } from "../safety/CrisisOverlay";
import { RefinementChips } from "../refinement/RefinementChips";
import { HumanSupportBanner } from "../support/HumanSupportBanner";

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
    environment: EnvironmentData;
    diversity: number;
    sessionMode: SessionMode;
  }) => string | null;
  quotaInfo?: QuotaInfo;
  onQuotaExhausted?: () => void;
  onLogout?: () => void;
}

const REFINE_METHOD_LABEL: Record<string, string> = {
  rule: "Rule engine",
  semantic_gate: "Semantic gate",
  deep_upgrade: "Deep mode",
};

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
  const [sessionMode, setSessionMode] = useState<SessionMode>("context");
  const [sseUrl, setSseUrl] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const { env, enabled: envEnabled, setEnabled: setEnvEnabled } = useEnvironment();
  const [diversity, setDiversity] = useState(0);
  // P2.3: Handoff tracking
  const [showHandoff, setShowHandoff] = useState(false);
  const [handoffSubmitted, setHandoffSubmitted] = useState(false);

  // --- Store selectors ---
  const emotion = useSessionStore((s) => s.emotion);
  const sseStatus = useSessionStore((s) => s.sseStatus);
  const crisis = useSessionStore((s) => s.crisis);
  const gate = useSessionStore((s) => s.gate);

  const generationPhase = useGenerationStore((s) => s.phase);
  const cards = useGenerationStore((s) => s.cards);
  const generationError = useGenerationStore((s) => s.error);

  // P0.1: Refinement state
  const isRefining = useGenerationStore((s) => s.isRefining);
  const refineAttempt = useGenerationStore((s) => s.refineAttempt);
  const refineMethod = useGenerationStore((s) => s.refineMethod);

  // P0.2: Lifecycle
  const sessionStatus = useSessionStore((s) => s.sessionStatus);
  const resumeInfo = useSessionStore((s) => s.resumeInfo);

  // P0.3: System notifications
  const notifications = useSessionStore((s) => s.notifications);
  const systemError = useSessionStore((s) => s.systemError);
  const dismissSystemError = useSessionStore((s) => s.dismissSystemError);

  // P2.4: Chat error
  const chatError = useSessionStore((s) => s.chatError);
  const setChatError = useSessionStore((s) => s.setChatError);

  const navigate = useNavigate();
  const { close } = useSSE({ url: sseUrl });
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
    const url = getSSEUrl({
      cardIds,
      freeText: freeText.trim(),
      sceneTag,
      intent,
      environment: envEnabled ? env : { season: null, time_of_day: null, weather_code: null, temperature: null, weather_label: null, weather_emoji: null },
      diversity,
      sessionMode,
    });
    if (!url) {
      onQuotaExhausted?.();
      return;
    }
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
    useSessionStore.getState().reset();    setShowHandoff(false);
    setHandoffSubmitted(false);
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

  const _buildBaseUrl = () => {
    return getSSEUrl({
      cardIds,
      freeText: freeText.trim(),
      sceneTag,
      intent,
      environment: envEnabled ? env : { season: null, time_of_day: null, weather_code: null, temperature: null, weather_label: null, weather_emoji: null },
      diversity,
      sessionMode,
    });
  };

  const handleRefine = (key: string) => {
    close();
    setSseUrl(null);
    const baseUrl = _buildBaseUrl();
    if (!baseUrl) return;
    const allergens = localStorage.getItem("perfume_allergens") || "";
    let refineUrl = `${baseUrl}&refine=${encodeURIComponent(key)}`;
    if (allergens) refineUrl += `&allergens=${encodeURIComponent(allergens)}`;
    track("refine_used", { keyword: key });    // Show handoff after 3rd refinement
    const attemptCount = useGenerationStore.getState().refineAttempt;
    if (attemptCount && attemptCount >= 3) {
      setShowHandoff(true);
    }
    setSseUrl(refineUrl);
  };

  const handleGateAnswer = (answer: string) => {
    close();
    setSseUrl(null);
    const baseUrl = _buildBaseUrl();
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

  // FR-5.5: Time-gated loading states
  const [loadingElapsed, setLoadingElapsed] = useState(0);
  useEffect(() => {
    if (!isGenerating) {
      setLoadingElapsed(0);
      return;
    }
    setLoadingElapsed(0);
    const timer = setInterval(() => {
      setLoadingElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isGenerating]);

  // P0.3: Auto-dismiss system notification toast
  const [visibleNotification, setVisibleNotification] = useState<typeof notifications[0] | null>(null);
  useEffect(() => {
    if (notifications.length > 0) {
      const latest = notifications[notifications.length - 1];
      setVisibleNotification(latest);
      const timer = setTimeout(() => setVisibleNotification(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [notifications]);

  const statusDot = {
    idle: "bg-stone-300",
    connecting: "bg-amber-400 animate-pulse",
    active: "bg-green-500",
    retrying: "bg-amber-500 animate-pulse",
    disconnected: "bg-red-500",
  }[sseStatus];

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col">
      <NetworkStatusBar />

      {/* P0.3: System notification toast */}
      <AnimatePresence>
        {visibleNotification && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-16 left-1/2 -translate-x-1/2 z-50 max-w-sm w-full px-4"
          >
            <div className="glass-card px-4 py-3 text-sm text-stone-700 shadow-md flex items-center gap-3">
              <span className="text-base">
                {visibleNotification.kind === "perfumer_update" ? "馃嵼" : "馃摚"}
              </span>
              <p className="flex-1">{visibleNotification.message}</p>
              <button
                onClick={() => setVisibleNotification(null)}
                className="text-stone-400 hover:text-stone-600 text-xs shrink-0"
              >
                鉁?
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* P0.3: System error banner */}
      <AnimatePresence>
        {systemError && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-red-50 border-b border-red-100"
          >
            <div className="max-w-2xl mx-auto px-4 py-2 flex items-center gap-3">
              <span className="text-red-500 text-xs shrink-0">馃揄</span>
              <p className="text-xs text-red-700 flex-1">{systemError.user_message}</p>
              {systemError.retryable && (
                <button
                  onClick={() => window.location.reload()}
                  className="text-xs text-red-600 underline underline-offset-2 shrink-0"
                >
                  Reload
                </button>
              )}
              <button
                onClick={dismissSystemError}
                className="text-red-400 hover:text-red-600 text-xs shrink-0"
              >
                鉁?
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* P0.2: Idle timeout banner */}
      <AnimatePresence>
        {sessionStatus === "idle_timeout" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-amber-50 border-b border-amber-100"
          >
            <div className="max-w-2xl mx-auto px-4 py-2 text-xs text-amber-700 text-center">
              Session timed out. Start a new conversation to continue.
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* P0.2: Resume banner */}
      <AnimatePresence>
        {resumeInfo && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-blue-50 border-b border-blue-100"
          >
            <div className="max-w-2xl mx-auto px-4 py-2 text-xs text-blue-700 text-center">
              Resuming from phase: {resumeInfo.from_phase}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Crisis overlay */}
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
            {hasStarted ? "鈫?New Session" : "鈫?Home"}
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
            Sessions: {quotaInfo.sessions?.remaining ?? "鈥?"}/
            {quotaInfo.sessions?.max ?? "鈥?"}
          </span>
          <span>
            Generations: {quotaInfo.generations?.remaining ?? "鈥?"}/
            {quotaInfo.generations?.max ?? "鈥?"}
          </span>
        </div>
      )}

      {/* P2.4: Chat error inline */}
      <AnimatePresence>
        {chatError && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="max-w-md mx-auto mt-3 glass-card px-4 py-2 text-center"
          >
            <p className="text-xs text-red-600">{chatError.user_message}</p>
            {chatError.retryable && (
              <button
                onClick={() => { setChatError(null); handleReset(); }}
                className="text-xs text-stone-500 underline underline-offset-2 mt-1"
              >
                Try again
              </button>
            )}
            <button
              onClick={() => setChatError(null)}
              className="text-xs text-stone-400 ml-2"
            >
              ✕
            </button>
          </motion.div>
        )}
        {/* P2.3: Human support banner — shown after 3 refinement attempts */}
        {showHandoff && !handoffSubmitted && (
          <div className="max-w-md mx-auto pt-4">
            <HumanSupportBanner
              visible={true}
              onHandoffSubmitted={(ticketId) => {
                setHandoffSubmitted(true);
              }}
              onDismiss={() => setShowHandoff(false)}
            />
          </div>
        )}

        {handoffSubmitted && (
          <div className="max-w-md mx-auto pt-4">
            <HumanSupportBanner
              visible={true}
              onDismiss={() => setHandoffSubmitted(false)}
            />
          </div>
        )}
      </AnimatePresence>

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
                    ? "馃幁 Pick a Card"
                    : "鉁嶏笍 Write how you feel"}
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
                Mode
              </p>
              <div className="flex justify-center">
                <SessionModeSelector
                  value={sessionMode}
                  onChange={setSessionMode}
                />
              </div>
            </div>

            <div>
              <p className="text-xs text-stone-400 text-center mb-3 font-medium uppercase tracking-wider">
                Optional 路 Scene
              </p>
              <div className="flex justify-center">
                <SceneTagChips
                  selected={[sceneTag]}
                  onToggle={handleToggleScene}
                />
              </div>
            </div>

            {envEnabled && (env.season || env.time_of_day || env.temperature !== null) && (
              <div className="flex items-center justify-center gap-2 text-xs text-stone-400">
                <span>{formatEnvironmentLabel(env)}</span>
                <button
                  onClick={() => setEnvEnabled(false)}
                  className="text-stone-300 hover:text-stone-500 transition-colors"
                  title="关关环境感知"
                >
                  鉁?
                </button>
              </div>
            )}

            <div>
              <p className="text-xs text-stone-400 text-center mb-2 font-medium uppercase tracking-wider">
                Style
              </p>
              <div className="flex justify-center gap-2">
                {[
                  { value: 0, label: "馃幆 精精准匹配" },
                  { value: 0.3, label: "鈿栵笍 均衡" },
                  { value: 0.6, label: "馃幉 惊喜探索" },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setDiversity(opt.value);
                      track("diversity_changed", { level: opt.value });
                    }}
                    className={`px-3 py-1.5 text-xs rounded-full transition-all
                      ${diversity === opt.value
                        ? "bg-stone-800 text-white shadow-sm"
                        : "bg-stone-200/50 text-stone-500 hover:bg-stone-200"
                      }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Agent Gate */}
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

        {/* P1.4: Refinement progress indicator */}
        {isRefining && (
          <div className="max-w-md mx-auto py-2">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center justify-center gap-2 text-xs text-stone-400"
            >
              <div className="w-3 h-3 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin" />
              <span>
                Refining
                {refineAttempt ? ` (attempt ${refineAttempt}/3)` : ""}
                {refineMethod ? ` \u00b7 ${REFINE_METHOD_LABEL[refineMethod] || refineMethod}` : ""}
              </span>
            </motion.div>
          </div>
        )}

        {/* Knowledge card carousel for >3s waits */}
        <KnowledgeCardOverlay visible={isGenerating && cards.length === 0 && loadingElapsed >= 3} />

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
          </motion.div>        )}

        {/* P2.3: Human support banner — shown after 3 refinement attempts */}
        {showHandoff && !handoffSubmitted && (
          <div className="max-w-md mx-auto pt-4">
            <HumanSupportBanner
              visible={true}
              onHandoffSubmitted={(ticketId) => {
                setHandoffSubmitted(true);
              }}
              onDismiss={() => setShowHandoff(false)}
            />
          </div>
        )}

        {handoffSubmitted && (
          <div className="max-w-md mx-auto pt-4">
            <HumanSupportBanner
              visible={true}
              onDismiss={() => setHandoffSubmitted(false)}
            />
          </div>
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
            <RefinementChips onSelect={handleRefine} />

            {shareUrl && (
              <div className="glass-card px-3 py-2 text-center text-xs text-green-700">
                Link copied! 馃搵
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

