import { Eyebrow } from "@/components/ui/card";

/** Routed placeholder for screens that land in later phases. */
export function ComingSoon({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>{phase}</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">{title}.</h1>
      </div>
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-hairline-strong bg-canvas-soft">
        <p className="font-mono text-body-sm text-mute">Coming in a later phase.</p>
      </div>
    </div>
  );
}
