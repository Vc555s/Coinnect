import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, Sparkles, Telescope } from "lucide-react";
import { Link } from "react-router-dom";
import { CategoryDot, SkillCard } from "@/components/SkillCard";
import { Avatar, ButtonLink, Empty, ErrorNote, PageHeader, Spinner, Trust } from "@/components/ui";
import { api, type Matches as M } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Matches() {
  const { me } = useAuth();
  const q = useQuery({ queryKey: ["matches"], queryFn: () => api<M>("/api/matches"), enabled: !!me });
  if (!q.data) return q.error ? <ErrorNote error={q.error} /> : <Spinner label="Matching" />;
  const { swaps, by_want, has_wants, has_offers } = q.data;

  return (
    <>
      <PageHeader eyebrow="Matches" title={<>People who fit your <em className="text-coin-deep">wishlist</em></>}>
        Matching compares skill names loosely, so “JS” finds “JavaScript” and “Python” finds “Python programming”. Swaps are the
        rare double fit: they teach what you want and want what you teach.
      </PageHeader>

      {!has_wants && (
        <Empty icon={<Telescope className="size-5" />} title="Add something you want to learn">
          Matches come from your wishlist.{" "}
          <Link to="/me#skills" className="font-medium text-ink underline">
            Add a wanted skill
          </Link>{" "}
          on your dashboard.
        </Empty>
      )}

      {swaps.length > 0 && (
        <section className="mb-16">
          <h2 className="display mb-2 flex items-center gap-2 text-3xl">
            <Sparkles className="size-6 text-coin" /> Perfect swaps
          </h2>
          <p className="mb-6 text-sm text-muted">Teach each other and both balances stay level.</p>
          <div className="grid gap-5 lg:grid-cols-2">
            {swaps.map((s) => (
              <article key={`${s.you_get.id}-${s.you_give.id}`} className="card animate-rise overflow-hidden">
                <div className="flex items-center gap-3 border-b border-line p-5">
                  <Avatar name={s.you_get.owner.name} id={s.you_get.owner.id} size={42} />
                  <div className="flex-1">
                    <Link to={`/u/${s.you_get.owner.id}`} className="font-medium hover:underline">
                      {s.you_get.owner.name}
                    </Link>
                    <Trust value={s.you_get.owner.trust} count={s.you_get.owner.ratings} className="ml-2" />
                    <p className="text-xs text-muted">{s.you_get.owner.headline}</p>
                  </div>
                  <span className="font-mono text-xs text-verdigris">{Math.round(s.score * 100)}%</span>
                </div>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 p-5">
                  <div>
                    <p className="eyebrow mb-1">You learn</p>
                    <p className="display text-lg leading-tight">{s.you_get.name}</p>
                    <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-muted">
                      <CategoryDot category={s.you_get.category} /> {s.you_get.rate} coins
                    </p>
                  </div>
                  <span className="grid size-10 place-items-center rounded-full bg-coin-soft text-coin-deep">
                    <ArrowLeftRight className="size-4" />
                  </span>
                  <div className="text-right">
                    <p className="eyebrow mb-1">You teach</p>
                    <p className="display text-lg leading-tight">{s.you_give.name}</p>
                    <p className="mt-1 text-xs text-muted">they asked for “{s.their_request.name}”</p>
                  </div>
                </div>
                <div className="flex justify-end border-t border-dashed border-line px-5 py-3">
                  <ButtonLink to={`/u/${s.you_get.owner.id}`} size="sm" variant="outline">
                    Open profile
                  </ButtonLink>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {by_want.map((g) => (
        <section key={g.want.id} className="mb-14">
          <div className="mb-5 flex flex-wrap items-baseline gap-3 border-b border-line pb-3">
            <span className="eyebrow">You want</span>
            <h2 className="display text-2xl">{g.want.name}</h2>
            <span className="ml-auto text-sm text-muted">
              {g.offers.length ? `${g.offers.length} teacher${g.offers.length > 1 ? "s" : ""}` : "no teachers yet"}
            </span>
          </div>
          {g.offers.length ? (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {g.offers.map((o, i) => (
                <SkillCard key={o.skill.id} skill={o.skill} score={o.score} delay={i * 40} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">Nobody offers this yet. We'll show teachers here as soon as someone lists it.</p>
          )}
        </section>
      ))}

      {has_wants && !has_offers && (
        <p className="mt-10 rounded-2xl bg-paper-2 p-5 text-sm text-ink-2">
          Tip: list something you can teach to unlock <b>Perfect swaps</b> and start earning coins.{" "}
          <Link to="/me#skills" className="font-medium underline">
            Add an offer
          </Link>
        </p>
      )}
    </>
  );
}
