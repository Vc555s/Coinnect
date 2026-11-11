import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, type Exchange, type Skill } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Avatar, Button, Coins, Dialog, ErrorNote } from "./ui";

export function RequestDialog({ skill, open, onClose }: { skill: Skill; open: boolean; onClose: () => void }) {
  const { me } = useAuth();
  const [message, setMessage] = useState("");
  const qc = useQueryClient();
  const nav = useNavigate();
  const book = useMutation({
    mutationFn: () => api<Exchange>("/api/exchanges", { method: "POST", body: { skill_id: skill.id, message } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["exchanges"] });
      toast.success(`Request sent to ${skill.owner.name.split(" ")[0]}`, { description: `${skill.rate} coins are held in escrow.` });
      onClose();
      nav("/me");
    },
  });
  const short = me ? me.balance < skill.rate : false;

  return (
    <Dialog open={open} onClose={onClose} title="Book a session">
      <div className="flex items-center gap-3 rounded-2xl bg-paper-2 p-4">
        <Avatar name={skill.owner.name} id={skill.owner.id} size={44} />
        <div className="min-w-0 flex-1">
          <p className="display truncate text-lg leading-tight">{skill.name}</p>
          <p className="text-sm text-muted">with {skill.owner.name}</p>
        </div>
        <Coins n={skill.rate} big className="text-lg font-semibold" />
      </div>

      <label className="label mt-5" htmlFor="msg">
        Message <span className="font-normal text-muted">(what do you want to cover?)</span>
      </label>
      <textarea
        id="msg"
        rows={3}
        className="input resize-none"
        value={message}
        maxLength={1000}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="I'd like to start with the basics and build something small…"
      />

      <div className="mt-4 flex gap-3 rounded-xl border border-verdigris/25 bg-verdigris-soft p-3 text-[13px] leading-relaxed text-ink-2">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-verdigris" />
        <p>
          Your coins go into escrow, not to the teacher. They're released only when <b>you</b> confirm the session happened, and
          refunded if the request is declined or you cancel.
        </p>
      </div>

      {book.error && (
        <div className="mt-4">
          <ErrorNote error={book.error} />
        </div>
      )}

      <div className="mt-6 flex items-center justify-between gap-3">
        <p className="text-xs text-muted">
          Balance after booking: <Coins n={Math.max(0, (me?.balance ?? 0) - skill.rate)} className="text-ink" />
        </p>
        <Button variant="coin" onClick={() => book.mutate()} loading={book.isPending} disabled={short}>
          {short ? "Not enough coins" : `Request · ${skill.rate} coins`}
        </Button>
      </div>
    </Dialog>
  );
}
