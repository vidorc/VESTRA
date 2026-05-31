/** Consistent page header across every screen: eyebrow + title, an optional
 * right-side slot for status/actions, and the hairline divider that anchors the
 * terminal layout. Titles are sentence-case + period-terminated (DESIGN.md). */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-lg border-b border-hairline pb-md">
      <div className="flex flex-wrap items-end justify-between gap-md">
        <div>
          <span className="font-mono text-caption uppercase tracking-wide text-mute">
            {eyebrow}
          </span>
          <h1 className="mt-xxs text-display-lg text-ink">{title}</h1>
        </div>
        {actions && <div className="flex items-center gap-md">{actions}</div>}
      </div>
      {description && <p className="mt-xs max-w-prose text-body-sm text-mute">{description}</p>}
    </div>
  );
}
