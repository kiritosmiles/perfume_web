import { type ReactNode } from "react";

interface ChatBodyProps {
  children: ReactNode;
}

export function ChatBody({ children }: ChatBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {children}
    </div>
  );
}
