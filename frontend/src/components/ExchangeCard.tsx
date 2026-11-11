import { useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, Check, ReceiptText, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, type Exchange } from "@/lib/api";
import { ago, shortCid } from "@/lib/format";
import { Avatar, Button, Coins, Dialog, ErrorNote, Stars } from "./ui";

const STATUS: Record<Exchange["status"], { label: string; cls: string }> = {
  pending: { label: "Awaiting teacher", cls: "bg-coin-soft text-coin-deep" },
  accepted: { label: "Scheduled", cls: "bg-verdigris-soft text-verdigris" },
  completed: { label: "Completed", cls: "bg-ink text-paper" },
  declined: { label: "Declined · refunded", cls: "bg-paper-2 text-muted" },
  cancelled: { label: "Cancelled · refunded", cls: "bg-paper-2 text-muted" },
};

export function needsMyAction(e: Exchange) {
  return (e.role === "provider" && e.status === "pending") || (e.role === "learner" && e.status === "accepted");
}

function RateDialog({ ex, open, onClose }: { ex: Exchange; open: boolean; onClose: () => void }) {
  const [score, setScore] = useState(5);
  const [comment, setComment] = useState("");
  const qc = useQueryClient();
  const other = ex.role === "provider" ? ex.learner : ex.provider;
  const rate = useMutation({
    mutationFn: () => api<Exchange>(`/api/exchanges/${ex.id}/rate`, { method: "POST", body: { score, comment } }),
    onSuccess: () => {
      qc.invalidateQueries();
      toast.success("Rating recorded on the ledger");
      onClose();
    },
  });
  return (
    <Dialog open={open} onClose={onClose} title={`Rate ${other.name.split(" ")[0]}`}>
      <p className="text-sm text-ink-2">
        How was <b>{ex.skill_name}</b>? Ratings feed into trust scores and are added to the public ledger.
      </p>
      <div className="my-5">
        <Stars value={score} onChange={setScore} />
      </div>
      <textarea className="input resize-none" rows={3} placeholder="Optional: a sentence for their profile" value={comment} maxLength={500} onChange={(e) => setComment(e.target.value)} />
      {rate.error && (
        <div className="mt-3">
          <ErrorNote error={rate.error} />
        </div>
      )}
      <div className="mt-5 flex justify-end">
        <Button onClick={() => rate.mutate()} loading={rate.isPending}>
          Submit rating
        </Button>
      </div>
    </Dialog>
  );
}

export function ExchangeCard({ ex }: { ex: Exchange }) {
  const qc = useQueryClient();
  const [rating, setRating] = useState(false);
  const act = useMutation({
    mutationFn: (action: "accept" | "decline" | "cancel" | "complete") =>
      api<Exchange>(`/api/exchanges/${ex.id}/${action}`, { method: "POST" }),
    onSuccess: (res, action) => {
      qc.invalidateQueries();
      const msg = {
        accept: "Accepted — arrange a time with your learner",
        decline: "Declined. Their coins were refunded",
        cancel: "Cancelled. Your coins are back in your wallet",
        complete: "Session confirmed. Receipt sealed on the ledger",
      }[action];
      toast.success(msg, res.receipt_cid ? { description: shortCid(res.receipt_cid, 16, 6) } : undefined);
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Action failed"),
  });

  const teaching = ex.role === "provider";
  const other = teaching ? ex.learner : ex.provider;
  const iRated = ex.ratings.some((r) => r.rater_id === (teaching ? ex.provider.id : ex.learner.id));
  const s = STATUS[ex.status];
  const busy = act.isPending ? act.variables : undefined;

  return (
    <article className={clsx("card animate-rise p-5", needsMyAction(ex) && "border-coin/60 shadow-[0_0_0_4px_var(--coin-soft)]")}>
      <div className="flex flex-wrap items-start gap-4">
        <Link to={`/u/${other.id}`}>
          <Avatar name={other.name} id={other.id} size={44} />
        </Link>
        <div className="min-w-0 flex-1">
          <p className="eyebrow mb-1">{teaching ? "You're teaching" : "You're learning"}</p>
          <p className="display text-xl leading-tight">{ex.skill_name}</p>
          <p className="mt-0.5 text-sm text-ink-2">
            {teaching ? "for" : "from"}{" "}
            <Link to={`/u/${other.id}`} className="font-medium hover:underline">
              {other.name}
            </Link>{" "}
            · <span className="text-muted">{ago(ex.updated_at)}</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={clsx("rounded-full px-2.5 py-1 text-[11px] font-medium", s.cls)}>{s.label}</span>
          <span className={clsx("text-sm font-medium", teaching ? "text-verdigris" : "text-ink")}>
            {teaching ? "+" : "−"}
            <Coins n={ex.amount} />
          </span>
        </div>
      </div>

      {ex.message && ex.status !== "completed" && (
        <blockquote className="mt-4 rounded-xl bg-paper-2 px-4 py-3 text-sm italic text-ink-2">“{ex.message}”</blockquote>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {teaching && ex.status === "pending" && (
          <>
            <Button size="sm" onClick={() => act.mutate("accept")} loading={busy === "accept"}>
              <Check className="size-4" /> Accept
            </Button>
            <Button size="sm" variant="danger" onClick={() => act.mutate("decline")} loading={busy === "decline"}>
              <X className="size-4" /> Decline
            </Button>
          </>
        )}
        {!teaching && ex.status === "accepted" && (
          <Button size="sm" variant="coin" onClick={() => act.mutate("complete")} loading={busy === "complete"}>
            <Check className="size-4" /> Session happened — release coins
          </Button>
        )}
        {!teaching && (ex.status === "pending" || ex.status === "accepted") && (
          <Button size="sm" variant="ghost" onClick={() => act.mutate("cancel")} loading={busy === "cancel"}>
            Cancel request
          </Button>
        )}
        {ex.status === "completed" && !iRated && (
          <Button size="sm" variant="outline" onClick={() => setRating(true)}>
            Rate {other.name.split(" ")[0]}
          </Button>
        )}
        {ex.receipt_cid && (
          <Link to={`/ledger/${ex.receipt_cid}`} className="ml-auto inline-flex items-center gap-1.5 font-mono text-xs text-muted hover:text-ink">
            <ReceiptText className="size-3.5" /> {shortCid(ex.receipt_cid)} <ArrowRight className="size-3" />
          </Link>
        )}
        {teaching && ex.status === "accepted" && <p className="text-xs text-muted">Waiting for {other.name.split(" ")[0]} to confirm the session.</p>}
        {!teaching && ex.status === "pending" && <p className="text-xs text-muted">Coins held in escrow until the session is done.</p>}
      </div>
      {ex.status === "completed" && <RateDialog ex={ex} open={rating} onClose={() => setRating(false)} />}
    </article>
  );
}
