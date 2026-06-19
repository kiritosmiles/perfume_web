import { Chip } from "../ui/Chip";

interface NotesCombinationProps {
  notes: string[];
}

const LAYER_LABELS = ["Top Notes 前调", "Middle Notes 中调", "Base Notes 尾调"];

export function NotesCombination({ notes }: NotesCombinationProps) {
  return (
    <div className="space-y-2">
      {notes.map((note, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-xs text-stone-400 w-28 shrink-0">
            {LAYER_LABELS[i] || ""}
          </span>
          <Chip
            label={note}
            selected={i === 1}
            disabled
          />
        </div>
      ))}
    </div>
  );
}
