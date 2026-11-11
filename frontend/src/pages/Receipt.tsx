import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowLeft, ArrowRight, BadgeCheck, ExternalLink, FileJson, MonitorCheck, ShieldX } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CopyCid, KindBadge, summarize } from "@/components/Ledger";
import { Button, Coins, ErrorNote, Spinner } from "@/components/ui";
import { api, rawUrl, type LedgerDetail } from "@/lib/api";
import { verifyRemote } from "@/lib/cid";
import { dateTime, shortCid } from "@/lib/format";

type Party = { id: number; name: string };

export default function Receipt() {
  const { cid = "" } = useParams();
  const [showRaw, setShowRaw] = useState(false);
  const q = useQuery({ queryKey: ["receipt", cid], queryFn: () => api<LedgerDetail>(`/api/ledger/${cid}`) });
  const local = useMutation({ mutationFn: () => verifyRemote(rawUrl(cid), cid) });

  if (q.error) return <ErrorNote error={q.error} />;
  if (!q.data) return <Spinner />;
  const e = q.data;
  const s = summarize(e);
  const d = e.record.data as Record<string, unknown>;
  const provider = d.provider as Party | undefined;
  const learner = d.learner as Party | undefined;

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/ledger" className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft className="size-4" /> Ledger
      </Link>

      <article className="perforated animate-rise rounded-3xl border border-line bg-card px-6 py-12 shadow-[0_40px_80px_-50px_rgba(22,20,15,.5)] sm:px-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <KindBadge kind={e.kind} />
            <span className="eyebrow">Entry #{e.seq}</span>
          </div>
          <span
            className={clsx(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
              e.verification.valid ? "bg-verdigris-soft text-verdigris" : "bg-rust-soft text-rust",
            )}
          >
            {e.verification.valid ? <BadgeCheck className="size-4" /> : <ShieldX className="size-4" />}
            {e.verification.valid ? "Hash verified by server" : "Hash mismatch"}
          </span>
        </div>

        <h1 className="display mt-8 text-5xl leading-[1.05]">{s.title}</h1>
        <p className="mt-2 text-lg text-ink-2">{s.line}</p>

        <div className="my-9 border-t-2 border-dashed border-line" />

        <dl className="grid gap-x-10 gap-y-5 sm:grid-cols-2">
          {provider && learner && (
            <>
              <Field label="Teacher">
                <Link className="hover:underline" to={`/u/${provider.id}`}>
                  {provider.name}
                </Link>
              </Field>
              <Field label="Learner">
                <Link className="hover:underline" to={`/u/${learner.id}`}>
                  {learner.name}
                </Link>
              </Field>
            </>
          )}
          {typeof d.amount === "number" && (
            <Field label="Amount">
              <Coins n={d.amount} big className="text-lg font-semibold" />
            </Field>
          )}
          {typeof d.score === "number" && <Field label="Score">{"★".repeat(d.score)}</Field>}
          <Field label="Sealed">{dateTime(e.created_at)}</Field>
          {typeof d.receipt === "string" && (
            <Field label="Rates receipt">
              <Link to={`/ledger/${d.receipt}`} className="font-mono text-sm hover:underline">
                {shortCid(d.receipt)}
              </Link>
            </Field>
          )}
        </dl>

        <div className="mt-9 space-y-4 rounded-2xl bg-paper-2 p-5">
          <Field label="Content ID (CIDv1 · raw · sha2-256)">
            <CopyCid cid={e.cid} full />
          </Field>
          <Field label="Previous entry">
            {e.prev_cid ? (
              <Link to={`/ledger/${e.prev_cid}`} className="break-all font-mono text-xs text-ink-2 hover:text-ink hover:underline">
                {e.prev_cid}
              </Link>
            ) : (
              <span className="font-mono text-xs text-muted">∅ — this is the genesis entry</span>
            )}
          </Field>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-start">
          <Button variant="coin" onClick={() => local.mutate()} loading={local.isPending}>
            <MonitorCheck className="size-4" /> Verify in my browser
          </Button>
          <div className="text-sm">
            {!local.data && !local.error && (
              <p className="text-muted">Downloads the raw bytes and recomputes the CID with WebCrypto — no trust in this server needed.</p>
            )}
            {local.data && (
              <p className={local.data.matches ? "text-verdigris" : "text-rust"}>
                {local.data.matches ? "✓ Match." : "✗ Mismatch!"} Your browser hashed {local.data.size} bytes to{" "}
                <span className="break-all font-mono text-xs">{local.data.computed}</span>
              </p>
            )}
            {local.error && <p className="text-rust">{(local.error as Error).message}</p>}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Button size="sm" variant="ghost" onClick={() => setShowRaw((v) => !v)}>
            <FileJson className="size-4" /> {showRaw ? "Hide" : "Show"} canonical JSON
          </Button>
          <a href={rawUrl(e.cid)} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs text-ink-2 hover:bg-paper-2">
            Raw bytes <ExternalLink className="size-3.5" />
          </a>
          {e.gateway_url && (
            <a href={e.gateway_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs text-ink-2 hover:bg-paper-2">
              Open on IPFS gateway <ExternalLink className="size-3.5" />
            </a>
          )}
        </div>
        {showRaw && (
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-ink p-5 font-mono text-xs leading-relaxed text-paper/90">
            {JSON.stringify(e.record, null, 2)}
          </pre>
        )}
      </article>

      <nav className="mt-8 flex justify-between text-sm">
        {e.prev_cid ? (
          <Link to={`/ledger/${e.prev_cid}`} className="inline-flex items-center gap-1.5 text-muted hover:text-ink">
            <ArrowLeft className="size-4" /> Older
          </Link>
        ) : (
          <span />
        )}
        {e.next_cid && (
          <Link to={`/ledger/${e.next_cid}`} className="inline-flex items-center gap-1.5 text-muted hover:text-ink">
            Newer <ArrowRight className="size-4" />
          </Link>
        )}
      </nav>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="eyebrow mb-1">{label}</dt>
      <dd className="text-[15px]">{children}</dd>
    </div>
  );
}
