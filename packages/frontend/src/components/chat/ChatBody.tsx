import { type ReactNode } from "react";

interface ChatBodyProps {
  children: ReactNode;
}

export function ChatBody({ children }: ChatBodyProps) {
  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-6 space-y-4 relative"
      style={{
        background: `radial-gradient(ellipse at 50% 30%, #fafaf9 0%, #f5f0eb 50%, #f0ebe4 100%)`,
      }}
    >
      {/* Subtle geometric SVG pattern (opacity 0.03) */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ opacity: 0.03 }}
      >
        <defs>
          <pattern
            id="geo-pattern"
            x="0" y="0" width="60" height="60"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="30" cy="30" r="1.5" fill="#292524" />
            <path d="M0 30 L60 30 M30 0 L30 60" stroke="#292524" strokeWidth="0.3" />
            <path d="M15 0 L0 15 M45 0 L60 15 M0 45 L15 60 M45 60 L60 45"
                  stroke="#292524" strokeWidth="0.2" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#geo-pattern)" />
      </svg>

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
