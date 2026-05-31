"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  digitalTwin,
  goals as goalsApi,
  type DigitalTwin,
  type Goal,
  type GoalType,
} from "@/lib/api";
import { inr } from "@/lib/utils";
import { Card, Eyebrow } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const EMPTY_TWIN: DigitalTwin = {
  age: undefined,
  annual_income: 0,
  monthly_expenses: 0,
  monthly_emi: 0,
  monthly_sip: 0,
  emergency_fund: 0,
  tax_bracket: 0,
  risk_profile: "moderate",
};

const TWIN_FIELDS: { key: keyof DigitalTwin; label: string }[] = [
  { key: "age", label: "Age" },
  { key: "annual_income", label: "Annual income (₹)" },
  { key: "monthly_expenses", label: "Monthly expenses (₹)" },
  { key: "monthly_emi", label: "Monthly EMI (₹)" },
  { key: "monthly_sip", label: "Monthly SIP (₹)" },
  { key: "emergency_fund", label: "Emergency fund (₹)" },
  { key: "tax_bracket", label: "Tax bracket (0–1)" },
];

const GOAL_TYPES: GoalType[] = [
  "retirement",
  "house",
  "education",
  "emergency_fund",
  "wealth_growth",
];

function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="h-9 w-full rounded-sm border border-hairline bg-canvas px-sm font-mono text-body-sm text-ink outline-none focus:border-hairline-strong"
    />
  );
}

function TwinSection() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["digital-twin"], queryFn: digitalTwin.get });
  const [twin, setTwin] = useState<DigitalTwin>(EMPTY_TWIN);

  useEffect(() => {
    if (data?.digital_twin) setTwin({ ...EMPTY_TWIN, ...data.digital_twin });
  }, [data]);

  const save = useMutation({
    mutationFn: () => digitalTwin.put(twin),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["digital-twin"] });
      qc.invalidateQueries({ queryKey: ["health"] });
    },
  });

  function set(key: keyof DigitalTwin, value: string) {
    setTwin((t) => ({
      ...t,
      [key]: key === "risk_profile" ? value : value === "" ? (key === "age" ? undefined : 0) : Number(value),
    }));
  }

  return (
    <Card>
      <Eyebrow>Digital Twin</Eyebrow>
      <p className="mt-xxs text-caption text-mute">
        Your financial context. Vestra reasons every decision against this.
      </p>
      <div className="mt-md grid grid-cols-1 gap-sm sm:grid-cols-2">
        {TWIN_FIELDS.map((f) => (
          <label key={f.key} className="block">
            <span className="font-mono text-caption uppercase text-mute">{f.label}</span>
            <Input
              type="number"
              value={(twin[f.key] ?? "") as number | string}
              onChange={(e) => set(f.key, e.target.value)}
            />
          </label>
        ))}
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Risk profile</span>
          <select
            value={twin.risk_profile}
            onChange={(e) => set("risk_profile", e.target.value)}
            className="h-9 w-full rounded-sm border border-hairline bg-canvas px-sm font-mono text-body-sm text-ink outline-none focus:border-hairline-strong"
          >
            <option value="conservative">conservative</option>
            <option value="moderate">moderate</option>
            <option value="aggressive">aggressive</option>
          </select>
        </label>
      </div>
      <div className="mt-md flex items-center gap-xs">
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save twin"}
        </Button>
        {save.isSuccess && <span className="text-caption text-up">Saved.</span>}
        {save.isError && <span className="text-caption text-down">Save failed.</span>}
      </div>
    </Card>
  );
}

function GoalsSection() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["goals"], queryFn: goalsApi.list });
  const [draft, setDraft] = useState<Omit<Goal, "goal_id">>({
    type: "retirement",
    name: "",
    target_amount: 0,
    current_amount: 0,
    target_date: "",
    priority: "medium",
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["goals"] });
    qc.invalidateQueries({ queryKey: ["health"] });
  };
  const create = useMutation({ mutationFn: () => goalsApi.create(draft), onSuccess: invalidate });
  const remove = useMutation({ mutationFn: (id: string) => goalsApi.remove(id), onSuccess: invalidate });

  const list = data?.goals ?? [];

  return (
    <Card>
      <Eyebrow>Goals</Eyebrow>
      <div className="mt-md space-y-sm">
        {list.map((g) => {
          const pct = g.target_amount > 0 ? Math.min(100, (g.current_amount / g.target_amount) * 100) : 100;
          return (
            <div key={g.goal_id} className="rounded-md border border-hairline p-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-xs">
                  <Badge tone={g.priority === "high" ? "warning" : "neutral"}>{g.type}</Badge>
                  <span className="text-body-sm text-ink">{g.name || g.type}</span>
                </div>
                <button
                  onClick={() => g.goal_id && remove.mutate(g.goal_id)}
                  className="font-mono text-caption text-mute hover:text-down"
                >
                  remove
                </button>
              </div>
              <div className="mt-xs flex items-center justify-between text-caption text-mute">
                <span>{inr(g.current_amount)} / {inr(g.target_amount)}</span>
                <span className="font-mono tnum">{Math.round(pct)}%</span>
              </div>
              <Progress value={pct} tone="up" className="mt-xxs" />
            </div>
          );
        })}
        {list.length === 0 && <p className="text-body-sm text-mute">No goals yet.</p>}
      </div>

      {/* Add goal */}
      <div className="mt-md grid grid-cols-1 gap-sm sm:grid-cols-2">
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Type</span>
          <select
            value={draft.type}
            onChange={(e) => setDraft((d) => ({ ...d, type: e.target.value as GoalType }))}
            className="h-9 w-full rounded-sm border border-hairline bg-canvas px-sm font-mono text-body-sm text-ink outline-none focus:border-hairline-strong"
          >
            {GOAL_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Name</span>
          <Input value={draft.name} onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))} />
        </label>
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Target amount (₹)</span>
          <Input
            type="number"
            value={draft.target_amount || ""}
            onChange={(e) => setDraft((d) => ({ ...d, target_amount: Number(e.target.value) }))}
          />
        </label>
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Current amount (₹)</span>
          <Input
            type="number"
            value={draft.current_amount || ""}
            onChange={(e) => setDraft((d) => ({ ...d, current_amount: Number(e.target.value) }))}
          />
        </label>
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Target date</span>
          <Input
            type="date"
            value={draft.target_date ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, target_date: e.target.value }))}
          />
        </label>
        <label className="block">
          <span className="font-mono text-caption uppercase text-mute">Priority</span>
          <select
            value={draft.priority}
            onChange={(e) => setDraft((d) => ({ ...d, priority: e.target.value as Goal["priority"] }))}
            className="h-9 w-full rounded-sm border border-hairline bg-canvas px-sm font-mono text-body-sm text-ink outline-none focus:border-hairline-strong"
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
      </div>
      <div className="mt-md">
        <Button
          variant="secondary"
          disabled={create.isPending || draft.target_amount <= 0}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Adding…" : "Add goal"}
        </Button>
      </div>
    </Card>
  );
}

export default function SettingsPage() {
  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>Profile & planning</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">Settings.</h1>
      </div>
      <div className="space-y-lg">
        <TwinSection />
        <GoalsSection />
      </div>
    </div>
  );
}
