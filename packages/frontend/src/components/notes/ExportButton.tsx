import { useState, useCallback } from "react";
import { toPng } from "html-to-image";
import { Button } from "../ui/Button";

interface ExportButtonProps {
  targetRef: React.RefObject<HTMLDivElement | null>;
  filename?: string;
}

type ExportState = "idle" | "loading" | "success" | "error";

export function ExportButton({ targetRef, filename }: ExportButtonProps) {
  const [state, setState] = useState<ExportState>("idle");

  const handleExport = useCallback(async () => {
    if (!targetRef.current) return;
    setState("loading");
    try {
      const dataUrl = await toPng(targetRef.current, {
        backgroundColor: "#f5f0eb",
        pixelRatio: 2,
        cacheBust: true,
      });
      const link = document.createElement("a");
      link.download = filename || `perfume-note-${new Date().toISOString().slice(0, 10)}.png`;
      link.href = dataUrl;
      link.click();
      setState("success");
      setTimeout(() => setState("idle"), 2000);
    } catch (err) {
      console.error("PNG export failed:", err);
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }, [targetRef, filename]);

  const label = {
    idle: "Save as Note",
    loading: "Generating...",
    success: "✓ Downloaded!",
    error: "Export failed — retry",
  }[state];

  return (
    <Button
      variant="glass"
      size="sm"
      onClick={handleExport}
      disabled={state === "loading"}
      className={state === "error" ? "text-red-500" : ""}
    >
      {label}
    </Button>
  );
}
