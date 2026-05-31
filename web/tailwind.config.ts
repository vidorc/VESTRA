import type { Config } from "tailwindcss";

/**
 * Vestra dark terminal theme.
 *
 * DESIGN.md specifies a *light* Vercel system (near-white canvas, ink text). The
 * product brief calls for a dark-mode-first Bloomberg terminal aesthetic, so we
 * invert the surface/ink polarity while preserving DESIGN.md's structural tokens:
 * the 4px spacing scale, the radius ladder, the type scale, the stacked-shadow
 * elevation model, and "mono for technical labels, geometric sans for narrative."
 */
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark surfaces (inverted polarity from DESIGN.md's canvas ladder).
        canvas: "#0a0a0a",
        "canvas-soft": "#111111",
        "canvas-soft-2": "#161616",
        panel: "#1a1a1a",
        hairline: "#262626",
        "hairline-strong": "#404040",
        // Ink -> light on dark.
        ink: "#ededed",
        body: "#a1a1a1",
        mute: "#6b6b6b",
        // Accents retained from DESIGN.md (the gradient/semantic palette).
        link: "#0070f3",
        success: "#0ac27e",
        error: "#ee0000",
        warning: "#f5a623",
        violet: "#7928ca",
        cyan: "#50e3c2",
        "highlight-pink": "#ff0080",
        // Financial up/down semantics (terminal convention).
        up: "#0ac27e",
        down: "#ff4d4d",
      },
      fontFamily: {
        // Geometric sans for narrative; mono for technical labels/numbers.
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        // DESIGN.md type scale (display uses negative tracking).
        "display-xl": ["48px", { lineHeight: "48px", letterSpacing: "-2.4px", fontWeight: "600" }],
        "display-lg": ["32px", { lineHeight: "40px", letterSpacing: "-1.28px", fontWeight: "600" }],
        "display-md": ["24px", { lineHeight: "32px", letterSpacing: "-0.96px", fontWeight: "600" }],
        "display-sm": ["20px", { lineHeight: "28px", letterSpacing: "-0.6px", fontWeight: "600" }],
        "body-lg": ["18px", { lineHeight: "28px" }],
        "body-md": ["16px", { lineHeight: "24px" }],
        "body-sm": ["14px", { lineHeight: "20px", letterSpacing: "-0.28px" }],
        caption: ["12px", { lineHeight: "16px" }],
      },
      spacing: {
        // 4px base unit ladder from DESIGN.md.
        xxs: "4px",
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "40px",
        "3xl": "48px",
        "4xl": "64px",
        "5xl": "96px",
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        pill: "100px",
      },
      boxShadow: {
        // Stacked-shadow elevation (tuned darker for the terminal surface).
        "level-2": "0px 1px 1px rgba(0,0,0,0.3), 0px 2px 2px rgba(0,0,0,0.2)",
        "level-3": "0px 2px 2px rgba(0,0,0,0.3), 0px 8px 8px -8px rgba(0,0,0,0.3)",
        "level-4": "0px 2px 2px rgba(0,0,0,0.3), 0px 8px 16px -4px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
