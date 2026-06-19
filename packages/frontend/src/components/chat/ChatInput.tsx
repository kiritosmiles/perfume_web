import { type ReactNode } from "react";

interface ChatInputProps {
  children: ReactNode;
  disabled?: boolean;
}

export function ChatInput({ children, disabled }: ChatInputProps) {
  return (
    <div className="sticky bottom-0 left-0 right-0 p-4">
      <div className={`
        glass-input flex flex-col gap-3 transition-opacity duration-300
        ${disabled ? "opacity-60 pointer-events-none" : ""}
      `}>
        {children}
      </div>
    </div>
  );
}
