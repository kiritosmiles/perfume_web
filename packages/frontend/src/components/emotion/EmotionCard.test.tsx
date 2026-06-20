import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmotionCard } from "./EmotionCard";

describe("EmotionCard", () => {
  it("renders emoji and label", () => {
    render(
      <EmotionCard
        id="joy"
        emoji="😊"
        label="开心"
        selected={false}
        disabled={false}
        onClick={() => {}}
      />
    );
    expect(screen.getByText("😊")).toBeInTheDocument();
    expect(screen.getByText("开心")).toBeInTheDocument();
  });

  it("applies selected ring when selected", () => {
    const { container } = render(
      <EmotionCard
        id="joy"
        emoji="😊"
        label="开心"
        selected={true}
        disabled={false}
        onClick={() => {}}
      />
    );
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toMatch(/ring-2/);
  });

  it("applies reduced opacity when disabled and not selected", () => {
    const { container } = render(
      <EmotionCard
        id="joy"
        emoji="😊"
        label="开心"
        selected={false}
        disabled={true}
        onClick={() => {}}
      />
    );
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toMatch(/opacity-40/);
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(
      <EmotionCard
        id="joy"
        emoji="😊"
        label="开心"
        selected={false}
        disabled={false}
        onClick={onClick}
      />
    );
    fireEvent.click(screen.getByText("😊"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not call onClick when disabled", () => {
    const onClick = vi.fn();
    render(
      <EmotionCard
        id="joy"
        emoji="😊"
        label="开心"
        selected={false}
        disabled={true}
        onClick={onClick}
      />
    );
    fireEvent.click(screen.getByText("😊"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
