"use client";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANTS: Record<Variant, string> = {
  // Marketing-scale pill CTA per DESIGN.md (ink primary, inverted for dark).
  primary: "bg-ink text-canvas hover:opacity-90",
  secondary: "bg-panel text-ink border border-hairline hover:border-hairline-strong",
  danger: "bg-down/15 text-down border border-down/40 hover:bg-down/25",
  ghost: "bg-transparent text-body hover:text-ink hover:bg-panel/60",
};

export function Button({
  variant = "primary",
  className,
  disabled,
  children,
  ...props
}: {
  variant?: Variant;
  className?: string;
  disabled?: boolean;
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      disabled={disabled}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-xs rounded-pill px-md font-mono text-body-sm font-medium transition-all disabled:opacity-50 disabled:pointer-events-none",
        VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
