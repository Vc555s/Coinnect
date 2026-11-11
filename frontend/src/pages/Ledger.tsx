import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ChainBlock } from "@/components/Ledger";
import { Button, ErrorNote, PageHeader, Segmented, Spinner } from "@/components/ui";
import { api, type ChainCheck, type LedgerEntry } from "@/lib/api";
import { shortCid } from "@/lib/format";

type Page = { total: number; entries: LedgerEntry[]; ipfs_pinning: boolean };

export default function Ledger() {
  const [kind, setKind] = useState<"all" | "exchange" | "rating">("all");
  const pages = useInfiniteQuery({
    queryKey: ["ledger", kind],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      api<Page>(`/api/ledger?limit=20${pageParam ? `&before=${pageParam}` : ""}${kind !== "all" ? `&kind=${kind}` : ""}`),
    getNextPageParam: (last) => (last.entries.length === 20 ? last.entries[last.entries.length - 1]!.seq : undefined),
  });
  const verify = useMutation({ mutationFn: () => api<ChainCheck>("/api/ledger/verify") });
  const entries = pages.data?.pages.flatMap((p) => p.entries) ?? [];
  const first = pages.data?.pages[0];

  return (
    <div className="grid gap-12 lg:grid-cols-[1fr_20rem]">
      <div>
        <PageHeader eyebrow="Public ledger" title={<>Every session, <em className="text-coin-deep">sealed</em>.</>}>
          Each entry is canonical JSON identified by its IPFS CID (CIDv1, sha-256) and holds the CID of the entry before it.
          Change one byte anywhere and every later link breaks.
        </PageHeader>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Segmented
            value={kind}
            onChange={setKind}
            options={[
              { value: "all", label: "All" },
              { value: "exchange", label: "Sessions" },
              { value: "rating", label: "Ratings" },
            ]}
          />
          {first && <span className="font-mono text-xs text-muted">{first.total} entries</span>}
        </div>
        {pages.isLoading ? (
          <Spinner />
        ) : pages.error ? (
          <ErrorNote error={pages.error} />
        ) : (
          <ol>
            {entries.map((e, i) => (
              <ChainBlock key={e.cid} entry={e} last={i === entries.length - 1} />
            ))}
          </ol>
        )}
        {pages.hasNextPage && (
          <div className="flex justify-center">
            <Button variant="outline" onClick={() => pages.fetchNextPage()} loading={pages.isFetchingNextPage}>
              Load older entries
            </Button>
          </div>
        )}
      </div>

      <aside className="lg:sticky lg:top-24 lg:self-start">
        <div className="card p-6">
          <h2 className="display text-2xl">Audit the chain</h2>
          <p className="mt-2 text-sm text-ink-2">The server re-hashes every entry and walks the links from genesis to head.</p>
          <Button className="mt-5 w-full" onClick={() => verify.mutate()} loading={verify.isPending}>
            Verify all entries
          </Button>
          {verify.data && (
            <div
              className={clsx(
                "mt-4 flex gap-3 rounded-xl p-4 text-sm",
                verify.data.valid ? "bg-verdigris-soft text-verdigris" : "bg-rust-soft text-rust",
              )}
            >
              {verify.data.valid ? <ShieldCheck className="size-5 shrink-0" /> : <ShieldAlert className="size-5 shrink-0" />}
              <div>
                <p className="font-medium">
                  {verify.data.valid ? `All ${verify.data.length} entries intact` : verify.data.problem}
                </p>
                {verify.data.valid && verify.data.head && (
                  <p className="mt-1 font-mono text-xs opacity-80">head {shortCid(verify.data.head)}</p>
                )}
                {verify.data.broken_at && (
                  <Link to={`/ledger/${verify.data.broken_at}`} className="mt-1 block font-mono text-xs underline">
                    {shortCid(verify.data.broken_at)}
                  </Link>
                )}
              </div>
            </div>
          )}
          {verify.error && <ErrorNote error={verify.error} />}
          <p className="mt-5 border-t border-dashed border-line pt-4 text-xs leading-relaxed text-muted">
            Don't want to trust the server? Open any receipt and verify it in your browser, or run{" "}
            <code className="font-mono">ipfs add --cid-version=1 --raw-leaves</code> on its raw bytes.
          </p>
          <p className="mt-3 text-xs text-muted">
            IPFS pinning: <b className="text-ink-2">{first?.ipfs_pinning ? "enabled" : "off (receipts are still content-addressed)"}</b>
          </p>
        </div>
      </aside>
    </div>
  );
}
