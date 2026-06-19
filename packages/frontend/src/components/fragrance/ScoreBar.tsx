interface ScoreBarProps {
  score: number;
  source: string;
}

const sourceLabels: Record<string, string> = {
  graphrag_match: "GraphRAG",
  template_fallback: "Template",
  llm_composer: "AI",
};

export function ScoreBar({ score, source }: ScoreBarProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-stone-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-stone-700 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-sm font-medium text-stone-700">{score}%</span>
      <span className="text-xs text-stone-400 bg-stone-100 rounded-full px-2 py-0.5">
        {sourceLabels[source] || source}
      </span>
    </div>
  );
}
