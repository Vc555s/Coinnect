import clsx from "clsx";
import { Check, Copy, Link2, Sparkles, Star } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { LedgerEntry } from "@/lib/api";
import { ago, shortCid } from "@/lib/format";
import { Coins } from "./ui";

type Party = { id: number; name: string };

export function summarize(e: Pick<LedgerEntry, "kind" | "record">) {
  const d = e.record.data as Record<string, unknown>;
  if (e.kind === "exchange") {
    const p = d.provider as Party;
    const l = d.learner as Party;
    return { title: d.skill as string, line: `${p.name} taught ${l.name}`, amount: d.amount as number };
  }
  if (e.kind === "rating") {
    const stars = "★".repeat(d.score as number);
    if (d.rater && d.ratee)
      return { title: `${stars} for ${(d.ratee as Party).name}`, line: `${(d.rater as Party).name} rated “${d.skill}”` };
    return { title: `${stars} rating`, line: `For exchange #${d.exchange_id}` };
  }
  return { title: "Genesis", line: (d.note as string) ?? "Ledger initialised" };
}

export function KindBadge({ kind }: { kind: string }) {
  const style =
    kind === "exchange"
      ? "bg-coin-soft text-coin-deep"
      : kind === "rating"
        ? "bg-verdigris-soft text-verdigris"
        : "bg-paper-2 text-ink-2";
  const Icon = kind === "exchange" ? Link2 : kind === "rating" ? Star : Sparkles;
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider", style)}>
      <Icon className="size-3" /> {kind}
    </span>
  );
}

export function CopyCid({ cid, full }: { cid: string; full?: boolean }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        navigator.clipboard?.writeText(cid).then(() => {
          setDone(true);
          setTimeout(() => setDone(false), 1400);
        });
      }}
      className="group inline-flex max-w-full items-center gap-1.5 rounded-md font-mono text-xs text-ink-2 hover:text-ink"
      title="Copy CID"
    >
      <span className={clsx(full ? "break-all text-left" : "truncate")}>{full ? cid : shortCid(cid)}</span>
      {done ? <Check className="size-3.5 shrink-0 text-verdigris" /> : <Copy className="size-3.5 shrink-0 opacity-0 transition group-hover:opacity-100" />}
    </button>
  );
}

/** One block in the chain view; the rail on the left draws the hash links. */
export function ChainBlock({ entry, last }: { entry: LedgerEntry; last?: boolean }) {
  const s = summarize(entry);
  return (
    <li className="relative grid grid-cols-[2.5rem_1fr] gap-4">
      <div className="relative flex justify-center">
        <span
          className={clsx(
            "relative z-10 mt-5 grid size-9 place-items-center rounded-full border-2 font-mono text-[11px]",
            entry.kind === "exchange" ? "border-coin bg-coin-soft text-coin-deep" : "border-line bg-card text-muted",
          )}
        >
          {entry.seq}
        </span>
        {!last && <span className="absolute top-14 bottom-[-1.25rem] w-px border-l-2 border-dotted border-line" />}
      </div>
      <Link
        to={`/ledger/${entry.cid}`}
        className="card group mb-5 block p-4 transition hover:border-ink-2/40 hover:shadow-[0_14px_30px_-22px_rgba(22,20,15,.4)] sm:p-5"
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <KindBadge kind={entry.kind} />
          <span className="text-xs text-muted">{ago(entry.created_at)}</span>
          {entry.pinned && <span className="chip border-verdigris/30 text-verdigris">pinned on IPFS</span>}
          {s.amount !== undefined && <Coins n={s.amount} className="ml-auto text-sm font-medium" />}
        </div>
        <p className="display mt-2 text-lg leading-snug">{s.title}</p>
        <p className="text-sm text-ink-2">{s.line}</p>
        <div className="mt-3 grid gap-1 border-t border-dashed border-line pt-3 font-mono text-[11px] text-muted sm:grid-cols-2">
          <span className="truncate">
            cid <span className="text-ink-2">{shortCid(entry.cid, 14, 8)}</span>
          </span>
          <span className="truncate">
            prev <span className="text-ink-2">{entry.prev_cid ? shortCid(entry.prev_cid, 14, 8) : "∅ (genesis)"}</span>
          </span>
        </div>
      </Link>
    </li>
  );
}
