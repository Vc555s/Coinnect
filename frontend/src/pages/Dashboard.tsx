import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Inbox, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ExchangeCard, needsMyAction } from "@/components/ExchangeCard";
import { CategoryDot } from "@/components/SkillCard";
import { Button, Coins, Dialog, Empty, ErrorNote, Segmented, Spinner, Trust } from "@/components/ui";
import { api, type Exchange, type Skill, type SkillKind } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const LEVELS = ["beginner", "intermediate", "advanced", "expert"];

function AddSkillDialog({ open, onClose, kind }: { open: boolean; onClose: () => void; kind: SkillKind }) {
  const qc = useQueryClient();
  const cats = useQuery({ queryKey: ["categories"], queryFn: () => api<string[]>("/api/skills/categories"), staleTime: Infinity });
  const [form, setForm] = useState({ name: "", category: "Tech", level: "intermediate", rate: 2, availability: "Flexible", description: "" });
  const add = useMutation({
    mutationFn: () => api<Skill>("/api/skills", { method: "POST", body: { ...form, kind } }),
    onSuccess: (s) => {
      qc.invalidateQueries();
      toast.success(kind === "offer" ? `“${s.name}” is now on offer` : `Added “${s.name}” to your wishlist`);
      setForm((f) => ({ ...f, name: "", description: "" }));
      onClose();
    },
  });
  const field = (k: keyof typeof form) => ({
    value: form[k],
    onChange: (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: k === "rate" ? Number(e.target.value) : e.target.value })),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };

  return (
    <Dialog open={open} onClose={onClose} title={kind === "offer" ? "Offer a skill" : "Add to your wishlist"}>
      <form onSubmit={submit} className="grid gap-4">
        <div>
          <label className="label">Skill</label>
          <input className="input" required minLength={2} maxLength={80} placeholder={kind === "offer" ? "e.g. Intro to guitar" : "e.g. Public speaking"} {...field("name")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Category</label>
            <select className="input" {...field("category")}>
              {(cats.data ?? ["Other"]).map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          {kind === "offer" && (
            <div>
              <label className="label">Your level</label>
              <select className="input capitalize" {...field("level")}>
                {LEVELS.map((l) => (
                  <option key={l}>{l}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        {kind === "offer" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Coins per session</label>
                <input className="input" type="number" min={1} max={50} {...field("rate")} />
              </div>
              <div>
                <label className="label">Availability</label>
                <input className="input" maxLength={80} {...field("availability")} />
              </div>
            </div>
            <div>
              <label className="label">What will a session cover?</label>
              <textarea className="input resize-none" rows={3} maxLength={1000} {...field("description")} />
            </div>
          </>
        )}
        {add.error && <ErrorNote error={add.error} />}
        <div className="flex justify-end">
          <Button loading={add.isPending}>{kind === "offer" ? "Publish offer" : "Add to wishlist"}</Button>
        </div>
      </form>
    </Dialog>
  );
}

function SkillsPanel() {
  const qc = useQueryClient();
  const skills = useQuery({ queryKey: ["my-skills"], queryFn: () => api<Skill[]>("/api/me/skills") });
  const [adding, setAdding] = useState<SkillKind | null>(null);
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/skills/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries(),
  });

  const groups: { kind: SkillKind; title: string; hint: string }[] = [
    { kind: "offer", title: "I can teach", hint: "Earn coins by teaching these." },
    { kind: "request", title: "I want to learn", hint: "Your wishlist drives your matches." },
  ];

  return (
    <section id="skills" className="grid gap-5 md:grid-cols-2">
      {groups.map((g) => {
        const items = skills.data?.filter((s) => s.kind === g.kind) ?? [];
        return (
          <div key={g.kind} className="card p-5">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h3 className="display text-xl">{g.title}</h3>
                <p className="text-xs text-muted">{g.hint}</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setAdding(g.kind)}>
                <Plus className="size-3.5" /> Add
              </Button>
            </div>
            {items.length ? (
              <ul className="divide-y divide-line">
                {items.map((s) => (
                  <li key={s.id} className="group flex items-center gap-3 py-2.5">
                    <CategoryDot category={s.category} />
                    <span className="flex-1 text-sm">{s.name}</span>
                    {s.kind === "offer" && <Coins n={s.rate} className="text-xs text-muted" />}
                    <button
                      onClick={() => remove.mutate(s.id)}
                      className="rounded-md p-1 text-muted opacity-0 transition hover:text-rust group-hover:opacity-100 focus:opacity-100"
                      aria-label={`Remove ${s.name}`}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-4 text-sm text-muted">Nothing yet.</p>
            )}
          </div>
        );
      })}
      {adding && <AddSkillDialog open kind={adding} onClose={() => setAdding(null)} />}
    </section>
  );
}

type Tab = "action" | "open" | "history";

export default function Dashboard() {
  const { me } = useAuth();
  const [tab, setTab] = useState<Tab>("action");
  const ex = useQuery({ queryKey: ["exchanges"], queryFn: () => api<Exchange[]>("/api/exchanges"), refetchInterval: 20000 });
  if (!me) return <Spinner />;

  const all = ex.data ?? [];
  const action = all.filter(needsMyAction);
  const open = all.filter((e) => (e.status === "pending" || e.status === "accepted") && !needsMyAction(e));
  const history = all.filter((e) => !["pending", "accepted"].includes(e.status));
  const list = { action, open, history }[tab];
  const earned = history.filter((e) => e.status === "completed" && e.role === "provider").reduce((n, e) => n + e.amount, 0);

  return (
    <>
      <header className="mb-10 animate-rise">
        <p className="eyebrow mb-3">Dashboard</p>
        <h1 className="display text-4xl sm:text-5xl">Hello, {me.name.split(" ")[0]}.</h1>
      </header>

      <section className="mb-12 grid gap-5 lg:grid-cols-[1.3fr_1fr_1fr]">
        <div className="relative overflow-hidden rounded-3xl bg-ink p-7 text-paper">
          <div className="absolute -top-16 -right-16 size-48 rounded-full border-[18px] border-coin/70" aria-hidden />
          <p className="eyebrow !text-paper/60">Wallet</p>
          <p className="display relative mt-4 flex items-baseline gap-3 text-6xl tabular-nums">
            {me.balance}
            <span className="font-sans text-base text-paper/60">SkillCoins</span>
          </p>
          <p className="mt-4 text-sm text-paper/70">
            {me.escrow ? (
              <>
                <b className="text-coin">{me.escrow}</b> more held in escrow for open bookings
              </>
            ) : (
              "Nothing held in escrow"
            )}
          </p>
        </div>
        <div className="card p-6">
          <p className="eyebrow">Trust</p>
          <p className="display mt-3 text-5xl tabular-nums">{me.trust.toFixed(2)}</p>
          <Trust value={me.trust} count={me.ratings} className="mt-2" />
          <p className="mt-2 text-xs text-muted">Bayesian average — new members start at 4.0 and move with each rating.</p>
        </div>
        <div className="card p-6">
          <p className="eyebrow">Teaching</p>
          <p className="display mt-3 text-5xl tabular-nums">{me.sessions_taught}</p>
          <p className="mt-2 text-sm text-ink-2">sessions taught · {earned} coins earned</p>
        </div>
      </section>

      <section className="mb-14">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="display text-3xl">Exchanges</h2>
          <Segmented
            value={tab}
            onChange={setTab}
            options={[
              {
                value: "action",
                label: (
                  <>
                    Needs you
                    {action.length > 0 && <span className="ml-1.5 rounded-full bg-coin px-1.5 text-[11px] font-semibold text-[#16140f]">{action.length}</span>}
                  </>
                ),
              },
              { value: "open", label: `In progress (${open.length})` },
              { value: "history", label: "History" },
            ]}
          />
        </div>
        {ex.isLoading ? (
          <Spinner />
        ) : list.length ? (
          <div className={clsx("grid gap-4", tab === "history" && "lg:grid-cols-2")}>
            {list.map((e) => (
              <ExchangeCard key={e.id} ex={e} />
            ))}
          </div>
        ) : (
          <Empty icon={<Inbox className="size-5" />} title={tab === "action" ? "You're all caught up" : "Nothing here"}>
            {tab === "action" ? "Requests to accept and sessions to confirm will appear here." : "Book a session from Explore to get started."}
          </Empty>
        )}
      </section>

      <h2 className="display mb-5 text-3xl">Your skills</h2>
      <SkillsPanel />
    </>
  );
}
