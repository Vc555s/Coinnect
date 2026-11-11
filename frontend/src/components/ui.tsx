import clsx from "clsx";
import { Loader2, Star, X } from "lucide-react";
import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";
import { initials } from "@/lib/format";

type Variant = "primary" | "coin" | "ghost" | "outline" | "danger";
const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:bg-ink-2 shadow-[0_1px_0_rgba(255,255,255,.15)_inset]",
  coin: "bg-coin text-[#16140f] hover:brightness-105 shadow-[0_6px_20px_-8px_var(--coin)]",
  ghost: "text-ink-2 hover:bg-paper-2 hover:text-ink",
  outline: "border border-line bg-card text-ink hover:border-ink-2",
  danger: "border border-line bg-card text-rust hover:bg-rust-soft hover:border-rust/40",
};
const sizes = { sm: "h-8 px-3 text-xs gap-1.5", md: "h-10 px-4 text-sm gap-2", lg: "h-12 px-6 text-[15px] gap-2" };

export function Button({
  variant = "primary",
  size = "md",
  loading,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: keyof typeof sizes; loading?: boolean }) {
  return (
    <button
      className={clsx(
        "inline-flex select-none items-center justify-center whitespace-nowrap rounded-full font-medium transition active:scale-[.98] disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export function ButtonLink({
  variant = "primary",
  size = "md",
  className,
  ...rest
}: LinkProps & { variant?: Variant; size?: keyof typeof sizes }) {
  return (
    <Link
      className={clsx(
        "inline-flex items-center justify-center whitespace-nowrap rounded-full font-medium transition active:scale-[.98]",
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    />
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
        <circle cx="12.5" cy="16" r="7" fill="none" stroke="var(--coin)" strokeWidth="2.6" />
        <circle cx="19.5" cy="16" r="7" fill="none" stroke="currentColor" strokeWidth="2.6" />
      </svg>
      <span className="display text-[22px] font-semibold leading-none">Coinnect</span>
    </span>
  );
}

/** A SkillCoin amount. */
export function Coins({ n, className, big }: { n: number; className?: string; big?: boolean }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 font-mono tabular-nums", className)}>
      <span
        className={clsx(
          "grid place-items-center rounded-full bg-coin font-display font-bold text-[#16140f] ring-2 ring-coin-deep/30",
          big ? "size-7 text-sm" : "size-4 text-[9px]",
        )}
        aria-hidden
      >
        ¢
      </span>
      {n}
    </span>
  );
}

export function Avatar({ name, id, size = 36 }: { name: string; id: number; size?: number }) {
  const hue = (id * 67) % 360;
  return (
    <span
      className="inline-grid shrink-0 place-items-center rounded-full font-medium text-[#16140f]"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: `radial-gradient(circle at 30% 25%, oklch(0.93 0.06 ${hue}), oklch(0.78 0.11 ${hue}))`,
      }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

export function Trust({ value, count, className }: { value: number; count?: number; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 text-xs text-ink-2", className)} title="Trust score (Bayesian average of ratings)">
      <Star className="size-3.5 fill-coin text-coin" />
      <span className="font-medium tabular-nums text-ink">{value.toFixed(1)}</span>
      {count !== undefined && <span className="text-muted">({count})</span>}
    </span>
  );
}

export function Stars({ value, onChange }: { value: number; onChange?: (v: number) => void }) {
  return (
    <span className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={!onChange}
          onClick={() => onChange?.(n)}
          className={clsx("transition", onChange && "hover:scale-110")}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
        >
          <Star className={clsx("size-5", n <= value ? "fill-coin text-coin" : "text-line")} />
        </button>
      ))}
    </span>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: ReactNode }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-line bg-paper-2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "rounded-full px-4 py-1.5 text-sm transition",
            value === o.value ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Empty({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 border-dashed px-6 py-14 text-center">
      {icon && <div className="grid size-12 place-items-center rounded-full bg-paper-2 text-muted">{icon}</div>}
      <p className="display text-xl">{title}</p>
      {children && <div className="max-w-sm text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
      <Loader2 className="size-4 animate-spin" /> {label}…
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  return (
    <div className="rounded-xl border border-rust/30 bg-rust-soft px-4 py-3 text-sm text-rust">
      {error instanceof Error ? error.message : "Something went wrong."}
    </div>
  );
}

export function Dialog({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className={clsx(
        "m-auto w-[calc(100%-2rem)] rounded-3xl border border-line bg-card p-0 text-ink shadow-2xl backdrop:bg-ink/40 backdrop:backdrop-blur-sm",
        wide ? "max-w-2xl" : "max-w-lg",
      )}
    >
      {open && (
        <div className="p-6 sm:p-7">
          <div className="mb-5 flex items-start justify-between gap-4">
            <h2 className="display text-2xl">{title}</h2>
            <button onClick={onClose} className="rounded-full p-1.5 text-muted hover:bg-paper-2 hover:text-ink" aria-label="Close">
              <X className="size-5" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-10 animate-rise">
      {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
      <h1 className="display text-4xl leading-[1.05] sm:text-5xl">{title}</h1>
      {children && <div className="mt-4 max-w-2xl text-[15px] leading-relaxed text-ink-2">{children}</div>}
    </header>
  );
}
