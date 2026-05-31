"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { auth, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res =
        mode === "login"
          ? await auth.login(email, password)
          : await auth.register(email, password);
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Something went wrong.";
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas px-md">
      {/* Ambient mesh glow — the brand's signature decoration, hero scale only,
          tuned dark so it reads as atmosphere rather than chrome (DESIGN.md). */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-1/3 left-1/2 h-[640px] w-[640px] -translate-x-1/2 rounded-full opacity-[0.18] blur-[120px]"
        style={{
          background:
            "conic-gradient(from 180deg, #0070f3, #50e3c2, #7928ca, #ff0080, #f5a623, #0070f3)",
        }}
      />
      {/* Faint grid texture for the terminal feel, masked to fade at the edges. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(#262626 1px, transparent 1px), linear-gradient(90deg, #262626 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 60% 50% at 50% 40%, black, transparent)",
          WebkitMaskImage: "radial-gradient(ellipse 60% 50% at 50% 40%, black, transparent)",
        }}
      />

      <div className="relative w-full max-w-sm">
        <div className="mb-lg flex flex-col items-center text-center">
          <span className="grid h-10 w-10 place-items-center rounded-md bg-ink font-mono text-display-sm font-semibold text-canvas shadow-level-3">
            V
          </span>
          <span className="mt-sm font-mono text-display-md font-semibold tracking-tight text-ink">
            vestra
          </span>
          <p className="mt-xxs text-body-sm text-mute">AI Wealth Operating System</p>
        </div>

        <div className="rounded-lg border border-hairline bg-canvas-soft/80 p-xl shadow-level-4 backdrop-blur-sm">
          <div className="mb-lg grid grid-cols-2 gap-xxs rounded-md bg-canvas p-xxs">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className={cn(
                  "rounded-sm px-sm py-xs text-body-sm transition-all duration-150",
                  mode === m
                    ? "bg-panel text-ink shadow-level-2"
                    : "text-mute hover:text-body",
                )}
              >
                {m === "register" ? "Sign up" : "Sign in"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-md">
            <div>
              <label className="font-mono text-caption uppercase tracking-wide text-mute">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-xxs h-10 w-full rounded-sm border border-hairline bg-canvas px-sm text-body-sm text-ink outline-none transition-colors placeholder:text-mute focus:border-link"
              />
            </div>
            <div>
              <label className="font-mono text-caption uppercase tracking-wide text-mute">
                Password
              </label>
              <input
                type="password"
                required
                minLength={mode === "register" ? 8 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-xxs h-10 w-full rounded-sm border border-hairline bg-canvas px-sm text-body-sm text-ink outline-none transition-colors placeholder:text-mute focus:border-link"
              />
              {mode === "register" && (
                <p className="mt-xxs text-caption text-mute">At least 8 characters.</p>
              )}
            </div>

            {error && (
              <p className="rounded-sm border border-down/30 bg-down/10 px-sm py-xs text-body-sm text-down">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="h-10 w-full rounded-pill bg-ink font-mono text-body-sm font-medium text-canvas transition-all hover:opacity-90 active:scale-[0.99] disabled:opacity-50"
            >
              {busy ? "…" : mode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="mt-md text-center font-mono text-caption text-mute">
          Indian equity markets · NSE · BSE
        </p>
      </div>
    </div>
  );
}
