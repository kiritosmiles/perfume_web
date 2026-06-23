import { Chip } from "../ui/Chip";
import type { NotesPyramid } from "@perfume/shared";

interface NotesCombinationProps {
  notes: NotesPyramid;
}

const LAYER_SPEC: Array<{ key: keyof NotesPyramid; label: string }> = [
  { key: "top", label: "Top Notes 前调" },
  { key: "middle", label: "Middle Notes 中调" },
  { key: "base", label: "Base Notes 尾调" },
];

export function NotesCombination({ notes }: NotesCombinationProps) {
  return (
    <div className="space-y-2">
      {LAYER_SPEC.map(({ key, label }) => {
        const items = notes[key];
        if (!items || items.length === 0) return null;
        return (
          <div key={key} className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-stone-400 w-30 shrink-0 leading-relaxed">
              {label}
            </span>
            <div className="flex flex-wrap gap-1">
              {items.map((note, i) => (
                <Chip
                  key={`${key}-${i}`}
                  label={note}
                  selected={key === "middle"}
                  disabled
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
