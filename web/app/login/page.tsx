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
    <div className="flex min-h-screen items-center justify-center bg-canvas px-md">
      <div className="w-full max-w-sm">
        <div className="mb-lg text-center">
          <span className="font-mono text-display-md font-semibold tracking-tight text-ink">
            vestra
          </span>
          <p className="mt-xxs text-body-sm text-mute">
            AI Wealth Operating System
          </p>
        </div>

        <div className="rounded-lg border border-hairline bg-canvas-soft p-xl shadow-level-4">
          <div className="mb-lg flex gap-xs">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className={cn(
                  "flex-1 rounded-sm px-sm py-xs text-body-sm capitalize transition-colors",
                  mode === m ? "bg-panel text-ink" : "text-body hover:text-ink",
                )}
              >
                {m === "register" ? "Sign up" : "Sign in"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-sm">
            <div>
              <label className="font-mono text-caption uppercase text-mute">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-xxs h-10 w-full rounded-sm border border-hairline bg-canvas px-sm text-body-sm text-ink outline-none focus:border-hairline-strong"
              />
            </div>
            <div>
              <label className="font-mono text-caption uppercase text-mute">Password</label>
              <input
                type="password"
                required
                minLength={mode === "register" ? 8 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-xxs h-10 w-full rounded-sm border border-hairline bg-canvas px-sm text-body-sm text-ink outline-none focus:border-hairline-strong"
              />
              {mode === "register" && (
                <p className="mt-xxs text-caption text-mute">At least 8 characters.</p>
              )}
            </div>

            {error && <p className="text-body-sm text-down">{error}</p>}

            <button
              type="submit"
              disabled={busy}
              className="h-10 w-full rounded-pill bg-ink font-mono text-body-sm font-medium text-canvas transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {busy ? "…" : mode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
