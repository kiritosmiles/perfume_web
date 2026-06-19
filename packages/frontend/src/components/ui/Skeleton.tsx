interface SkeletonProps {
  variant?: "text" | "card" | "title" | "avatar";
  className?: string;
}

const variantClasses: Record<string, string> = {
  text: "h-4 w-full",
  title: "h-6 w-2/3",
  card: "h-48 w-full",
  avatar: "h-16 w-16",
};

export function Skeleton({ variant = "text", className = "" }: SkeletonProps) {
  return (
    <div
      className={`
        rounded-lg animate-shimmer shimmer-bg
        ${variantClasses[variant]}
        ${className}
      `.trim()}
    />
  );
}
