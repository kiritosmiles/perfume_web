import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmotionCardPicker } from "./EmotionCardPicker";
import { BrowserRouter } from "react-router-dom";

// EmotionCardPicker uses react-router Link, wrap in BrowserRouter
function renderPicker(selectedIds: string[] = [], maxSelection = 2) {
  const onToggle = vi.fn();
  const result = render(
    <BrowserRouter>
      <EmotionCardPicker
        selectedIds={selectedIds}
        onToggle={onToggle}
        maxSelection={maxSelection}
      />
    </BrowserRouter>
  );
  return { onToggle, ...result };
}

describe("EmotionCardPicker", () => {
  it("renders all 8 emotion cards", () => {
    renderPicker();
    const cards = ["开心", "难过", "焦虑", "平静", "兴奋", "怀旧", "浪漫", "忧郁"];
    for (const label of cards) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("renders in a 2x4 grid", () => {
    const { container } = renderPicker();
    const grid = container.querySelector(".grid");
    expect(grid).toBeInTheDocument();
    expect(grid!.className).toMatch(/grid-cols-4/);
  });

  it("calls onToggle when a card is clicked", () => {
    const { onToggle } = renderPicker();
    fireEvent.click(screen.getByText("开心"));
    expect(onToggle).toHaveBeenCalledWith("joy");
  });

  it("disables unselected cards when at max selection", () => {
    renderPicker(["joy", "calm"], 2);
    // Cards that are NOT selected and NOT the first 2 should be disabled
    const cardElements = screen.getAllByRole("button"); // Each card is a button
    // All 8 cards rendered — those not selected should have opacity-40
    // Snapshot: count cards with disabled appearance
    const disabledCards = cardElements.filter(
      (el) => el.className.includes("opacity-40") || el.hasAttribute("disabled")
    );
    expect(disabledCards.length).toBeGreaterThanOrEqual(4);
  });
});
