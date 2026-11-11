import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { CategoryDot } from "@/components/SkillCard";
import { Avatar, ErrorNote, PageHeader, Spinner, Trust } from "@/components/ui";
import { api, type Member, type Signal, type Stats } from "@/lib/api";

function Bars({ title, rows, tone }: { title: string; rows: { name: string; count: number }[]; tone: "coin" | "verdigris" }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div className="card p-6">
      <h3 className="display mb-5 text-xl">{title}</h3>
      <ul className="space-y-3">
        {rows.map((r) => (
          <li key={r.name}>
            <Link to={`/explore?q=${encodeURIComponent(r.name)}`} className="group block">
              <div className="mb-1 flex justify-between text-sm">
                <span className="group-hover:underline">{r.name}</span>
                <span className="font-mono text-xs text-muted">{r.count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-paper-2">
                <div
                  className={clsx("h-full rounded-full transition-all duration-700", tone === "coin" ? "bg-coin" : "bg-verdigris")}
                  style={{ width: `${(r.count / max) * 100}%` }}
                />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

const SEVERITY = {
  high: "border-rust/40 bg-rust-soft text-rust",
  medium: "border-coin/40 bg-coin-soft text-coin-deep",
  low: "border-line bg-paper-2 text-ink-2",
};

export default function Insights() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api<Stats>("/api/stats") });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api<Member[]>("/api/members") });
  const integrity = useQuery({ queryKey: ["integrity"], queryFn: () => api<{ signals: Signal[] }>("/api/integrity") });
  if (stats.error) return <ErrorNote error={stats.error} />;
  if (!stats.data) return <Spinner />;
  const s = stats.data;
  const totalCat = s.categories.reduce((n, c) => n + c.count, 0) || 1;

  return (
    <>
      <PageHeader eyebrow="Insights" title="The state of the exchange">
        Supply and demand across the community, who's most trusted, and anything that looks off.
      </PageHeader>

      <section className="mb-10 grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          ["Offers listed", s.offers],
          ["Wishlist items", s.requests],
          ["Sessions completed", s.sessions],
          ["Receipts sealed", s.receipts],
        ].map(([k, v]) => (
          <div key={k} className="card p-5">
            <p className="display text-4xl tabular-nums">{v}</p>
            <p className="text-sm text-muted">{k}</p>
          </div>
        ))}
      </section>

      <section className="mb-10">
        <h3 className="eyebrow mb-3">Offers by category</h3>
        <div className="flex h-4 overflow-hidden rounded-full">
          {s.categories.map((c) => (
            <div key={c.name} title={`${c.name}: ${c.count}`} style={{ width: `${(c.count / totalCat) * 100}%` }} className="relative">
              <span className="absolute inset-0 [&>*]:!size-full [&>*]:!rounded-none">
                <CategoryDot category={c.name} />
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
          {s.categories.map((c) => (
            <span key={c.name} className="inline-flex items-center gap-1.5">
              <CategoryDot category={c.name} /> {c.name} · {c.count}
            </span>
          ))}
        </div>
      </section>

      <section className="mb-14 grid gap-5 md:grid-cols-2">
        <Bars title="Most offered" rows={s.top_offered} tone="coin" />
        <Bars title="Most wanted" rows={s.top_wanted} tone="verdigris" />
      </section>

      <section className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <h2 className="display mb-5 text-3xl">Most trusted</h2>
          <ol className="card divide-y divide-line">
            {(members.data ?? []).slice(0, 8).map((m, i) => (
              <li key={m.id}>
                <Link to={`/u/${m.id}`} className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-paper-2">
                  <span className="w-5 font-mono text-xs text-muted">{i + 1}</span>
                  <Avatar name={m.name} id={m.id} size={34} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{m.name}</p>
                    <p className="truncate text-xs text-muted">{m.headline}</p>
                  </div>
                  <Trust value={m.trust} count={m.ratings} />
                </Link>
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h2 className="display mb-5 text-3xl">Integrity signals</h2>
          {integrity.data?.signals.length ? (
            <ul className="space-y-3">
              {integrity.data.signals.map((sig, i) => (
                <li key={i} className={clsx("rounded-2xl border p-4", SEVERITY[sig.severity])}>
                  <div className="flex items-center justify-between text-xs uppercase tracking-wider">
                    <span>{sig.signal}</span>
                    <span>{sig.severity}</span>
                  </div>
                  <p className="mt-1.5 font-medium">{sig.name}</p>
                  <p className="text-sm opacity-90">{sig.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <div className="card flex gap-3 p-5 text-sm text-ink-2">
              <ShieldCheck className="size-5 shrink-0 text-verdigris" />
              <p>
                No signals right now. We watch for unproven skill breadth, listing bursts, low trust and members who only ever
                rate each other 5 stars.
              </p>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
