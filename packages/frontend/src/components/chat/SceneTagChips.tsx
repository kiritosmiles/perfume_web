import { Chip } from "../ui/Chip";

const SCENE_TAGS = [
  { id: "work", emoji: "💼", label: "通勤工作" },
  { id: "date", emoji: "💑", label: "约会之夜" },
  { id: "home", emoji: "🏠", label: "宅家放松" },
  { id: "party", emoji: "🎊", label: "聚会社交" },
];

interface SceneTagChipsProps {
  selected: string[];
  onToggle: (id: string) => void;
}

export function SceneTagChips({ selected, onToggle }: SceneTagChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {SCENE_TAGS.map((tag) => (
        <Chip
          key={tag.id}
          label={tag.label}
          emoji={tag.emoji}
          selected={selected.includes(tag.id)}
          onClick={() => onToggle(tag.id)}
        />
      ))}
    </div>
  );
}
