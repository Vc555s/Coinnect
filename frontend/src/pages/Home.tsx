import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, Handshake, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CopyCid, summarize } from "@/components/Ledger";
import { ButtonLink, Coins } from "@/components/ui";
import { api, type LedgerEntry, type Stats } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago } from "@/lib/format";

function HeroReceipt({ entry }: { entry?: LedgerEntry }) {
  const s = entry ? summarize(entry) : undefined;
  return (
    <div className="relative mx-auto w-full max-w-sm">
      {/* stacked slips behind */}
      <div className="absolute inset-0 translate-x-4 translate-y-5 rotate-3 rounded-2xl border border-line bg-paper-2" />
      <div className="absolute inset-0 translate-x-2 translate-y-2.5 rotate-[1.5deg] rounded-2xl border border-line bg-card/80" />
      <div className="perforated relative rounded-2xl border border-line bg-card px-7 py-9 shadow-[0_30px_60px_-30px_rgba(22,20,15,.45)]">
        <div className="flex items-center justify-between">
          <span className="eyebrow">Receipt #{entry?.seq ?? "—"}</span>
          <span className="inline-flex items-center gap-1 text-xs text-verdigris">
            <BadgeCheck className="size-3.5" /> sealed
          </span>
        </div>
        <p className="display mt-5 text-3xl leading-tight">{s?.title ?? "Python programming"}</p>
        <p className="mt-1 text-sm text-ink-2">{s?.line ?? "Asha taught Kabir"}</p>
        <div className="my-6 border-t-2 border-dashed border-line" />
        <dl className="space-y-2 font-mono text-xs">
          <div className="flex justify-between">
            <dt className="text-muted">amount</dt>
            <dd>
              <Coins n={s?.amount ?? 3} />
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">sealed</dt>
            <dd>{entry ? ago(entry.created_at) : "just now"}</dd>
          </div>
          <div className="flex justify-between gap-6">
            <dt className="text-muted">cid</dt>
            <dd className="min-w-0">{entry ? <CopyCid cid={entry.cid} /> : "bafkrei…"}</dd>
          </div>
        </dl>
        <div className="mt-6 flex h-8 items-end gap-[3px] opacity-70" aria-hidden>
          {Array.from({ length: 42 }, (_, i) => (
            <span key={i} className="w-[3px] bg-ink" style={{ height: `${30 + ((i * 37) % 70)}%` }} />
          ))}
        </div>
      </div>
      <div className="absolute -bottom-8 -left-2 grid size-20 sm:-left-7 animate-float place-items-center rounded-full bg-coin font-display text-3xl font-bold text-[#16140f] shadow-[0_18px_40px_-12px_var(--coin)] ring-8 ring-coin-soft">
        ¢
      </div>
    </div>
  );
}

const STEPS = [
  {
    icon: Search,
    title: "List what you know",
    body: "Offer the skills you can teach and wishlist the ones you want. Matching handles near-misses like “Python” and “Python programming”.",
  },
  {
    icon: Handshake,
    title: "Book with coins in escrow",
    body: "Every member starts with 10 SkillCoins. Booking holds the fee in escrow; it's released only when the learner confirms the session.",
  },
  {
    icon: BadgeCheck,
    title: "Get a sealed receipt",
    body: "Each finished session becomes a content-addressed receipt chained to the one before it. Anyone can re-hash it and check nothing changed.",
  },
];

export default function Home() {
  const { me } = useAuth();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api<Stats>("/api/stats") });
  const recent = useQuery({
    queryKey: ["ledger", "home"],
    queryFn: () => api<{ entries: LedgerEntry[] }>("/api/ledger?kind=exchange&limit=12"),
  });
  const entries = recent.data?.entries ?? [];
  const st = stats.data;

  return (
    <div className="-mt-4">
      {/* Hero */}
      <section className="grid items-center gap-16 overflow-x-clip pb-20 lg:grid-cols-[1.15fr_1fr]">
        <div className="animate-rise">
          <p className="eyebrow mb-6">Peer-to-peer skill exchange</p>
          <h1 className="display text-[clamp(3rem,8vw,6.2rem)] font-[450] leading-[0.92]">
            Trade what
            <br />
            you <em className="font-[350] text-coin-deep">know</em>.
          </h1>
          <p className="mt-7 max-w-lg text-lg leading-relaxed text-ink-2">
            Teach an hour, earn SkillCoins. Spend them learning something else from someone who loves it. No money changes hands
            — just knowledge, and a receipt nobody can quietly rewrite.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              nav(`/explore${q ? `?q=${encodeURIComponent(q)}` : ""}`);
            }}
            className="mt-9 flex max-w-lg items-center gap-2 rounded-full border border-line bg-card p-1.5 pl-5 shadow-[0_10px_30px_-20px_rgba(22,20,15,.4)] focus-within:border-coin"
          >
            <Search className="size-4 text-muted" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="What do you want to learn?"
              className="min-w-0 flex-1 bg-transparent py-2 text-[15px] outline-none placeholder:text-muted"
            />
            <button className="rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-paper transition hover:bg-ink-2">Search</button>
          </form>
          <div className="mt-5 flex flex-wrap items-center gap-2 text-sm text-muted">
            Popular:
            {(st?.top_wanted ?? []).slice(0, 4).map((t) => (
              <Link key={t.name} to={`/explore?q=${encodeURIComponent(t.name)}`} className="chip transition hover:border-ink-2 hover:text-ink">
                {t.name}
              </Link>
            ))}
          </div>
        </div>
        <div className="animate-rise [animation-delay:150ms]">
          <HeroReceipt entry={entries[0]} />
        </div>
      </section>

      {/* Stat strip */}
      <section className="grid grid-cols-2 border-y border-line md:grid-cols-4">
        {[
          { k: "Members", v: st?.members },
          { k: "Sessions completed", v: st?.sessions },
          { k: "Coins circulated", v: st?.coins_circulated },
          { k: "Average rating", v: st ? `${st.average_rating.toFixed(1)}★` : undefined },
        ].map((s, i) => (
          <div key={s.k} className={`px-5 py-8 ${i ? "md:border-l" : ""} ${i % 2 ? "border-l" : ""} border-line ${i > 1 ? "border-t md:border-t-0" : ""}`}>
            <p className="display text-4xl tabular-nums sm:text-5xl">{s.v ?? "–"}</p>
            <p className="mt-1 text-sm text-muted">{s.k}</p>
          </div>
        ))}
      </section>

      {/* Live ticker */}
      {entries.length > 2 && (
        <section className="overflow-hidden border-b border-line py-4 [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)]" aria-label="Recently sealed receipts">
          <div className="flex w-max animate-ticker gap-10 hover:[animation-play-state:paused]">
            {[...entries, ...entries].map((e, i) => {
              const s = summarize(e);
              return (
                <Link key={`${e.cid}-${i}`} to={`/ledger/${e.cid}`} className="flex shrink-0 items-center gap-3 text-sm">
                  <span className="size-1.5 rounded-full bg-coin" />
                  <span className="font-medium">{s.title}</span>
                  <span className="text-muted">{s.line}</span>
                  <span className="font-mono text-xs text-muted">{e.cid.slice(0, 12)}…</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* How it works */}
      <section className="py-24">
        <div className="mb-14 flex flex-wrap items-end justify-between gap-6">
          <h2 className="display max-w-xl text-4xl leading-tight sm:text-5xl">
            A small economy built on <em className="text-verdigris">trust</em>, not money.
          </h2>
          <ButtonLink to="/ledger" variant="outline">
            Inspect the ledger <ArrowRight className="size-4" />
          </ButtonLink>
        </div>
        <div className="grid gap-px overflow-hidden rounded-3xl border border-line bg-line md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="bg-card p-8">
              <div className="flex items-center justify-between">
                <span className="display text-6xl font-light text-coin-deep/80">{String(i + 1).padStart(2, "0")}</span>
                <s.icon className="size-6 text-muted" />
              </div>
              <h3 className="display mt-8 text-2xl">{s.title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden rounded-[2rem] bg-ink px-8 py-16 text-paper sm:px-14">
        <div className="absolute -right-24 -bottom-24 size-80 rounded-full border-[28px] border-coin/80" aria-hidden />
        <div className="absolute -right-4 -bottom-40 size-80 rounded-full border-[28px] border-paper/15" aria-hidden />
        <p className="eyebrow relative !text-paper/60">Your first 10 coins are on us</p>
        <h2 className="display relative mt-4 max-w-xl text-4xl leading-tight sm:text-5xl">Somebody wants to learn exactly what you know.</h2>
        <div className="relative mt-8 flex flex-wrap gap-3">
          {me ? (
            <ButtonLink to="/matches" variant="coin" size="lg">
              See your matches <ArrowRight className="size-4" />
            </ButtonLink>
          ) : (
            <>
              <ButtonLink to="/signup" variant="coin" size="lg">
                Create your account <ArrowRight className="size-4" />
              </ButtonLink>
              <ButtonLink to="/explore" size="lg" className="!bg-paper/10 !text-paper hover:!bg-paper/20">
                Browse first
              </ButtonLink>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
