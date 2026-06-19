import { type ReactNode } from "react";
import { motion } from "framer-motion";

interface ButtonProps {
  children: ReactNode;
  variant?: "glass" | "primary";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}

const variantClasses: Record<string, string> = {
  glass:
    "glass-card text-stone-700 hover:bg-white/90 active:bg-white/95",
  primary:
    "bg-stone-800 text-stone-50 hover:bg-stone-700 active:bg-stone-900 shadow-glass",
};

const sizeClasses: Record<string, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-3 text-base",
  lg: "px-8 py-4 text-lg",
};

export function Button({
  children,
  variant = "glass",
  size = "md",
  disabled = false,
  onClick,
  className = "",
}: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      onClick={onClick}
      disabled={disabled}
      className={`
        rounded-full font-medium transition-colors duration-200
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
        ${className}
      `.trim()}
    >
      {children}
    </motion.button>
  );
}
