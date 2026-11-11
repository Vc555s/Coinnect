import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { useParams } from "react-router-dom";
import { SkillCard } from "@/components/SkillCard";
import { Avatar, Empty, ErrorNote, Spinner, Stars, Trust } from "@/components/ui";
import { api, type Profile } from "@/lib/api";
import { ago, dateTime } from "@/lib/format";

export default function Member() {
  const { id } = useParams();
  const q = useQuery({ queryKey: ["member", id], queryFn: () => api<Profile>(`/api/members/${id}`) });
  if (q.error) return <ErrorNote error={q.error} />;
  if (!q.data) return <Spinner />;
  const { member: m, bio, joined, skills, reviews } = q.data;
  const offers = skills.filter((s) => s.kind === "offer");
  const wants = skills.filter((s) => s.kind === "request");

  return (
    <>
      <section className="mb-14 grid animate-rise gap-8 md:grid-cols-[auto_1fr_auto] md:items-center">
        <Avatar name={m.name} id={m.id} size={112} />
        <div>
          <h1 className="display text-5xl leading-none">{m.name}</h1>
          {m.headline && <p className="mt-3 text-lg text-ink-2">{m.headline}</p>}
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted">
            {m.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-4" /> {m.location}
              </span>
            )}
            <span>Joined {ago(joined)}</span>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-2xl border border-line bg-line text-center">
          {[
            ["Trust", m.trust.toFixed(1)],
            ["Ratings", m.ratings],
            ["Taught", m.sessions_taught],
          ].map(([k, v]) => (
            <div key={k} className="bg-card px-5 py-4">
              <dd className="display text-3xl tabular-nums">{v}</dd>
              <dt className="text-xs text-muted">{k}</dt>
            </div>
          ))}
        </dl>
      </section>

      {bio && <p className="ruled mb-14 max-w-3xl font-display text-2xl leading-8 text-ink-2">{bio}</p>}

      <h2 className="display mb-5 text-3xl">Teaches</h2>
      {offers.length ? (
        <div className="mb-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {offers.map((s, i) => (
            <SkillCard key={s.id} skill={s} delay={i * 40} />
          ))}
        </div>
      ) : (
        <div className="mb-14">
          <Empty title="No offers yet" />
        </div>
      )}

      {wants.length > 0 && (
        <>
          <h2 className="display mb-4 text-3xl">Wants to learn</h2>
          <div className="mb-14 flex flex-wrap gap-2">
            {wants.map((s) => (
              <span key={s.id} className="rounded-full border border-dashed border-ink-2/40 px-4 py-2 text-sm">
                {s.name}
              </span>
            ))}
          </div>
        </>
      )}

      <h2 className="display mb-5 text-3xl">Reviews</h2>
      {reviews.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {reviews.map((r, i) => (
            <figure key={i} className="card p-5">
              <div className="flex items-center justify-between">
                <Stars value={r.score} />
                <span className="text-xs text-muted" title={dateTime(r.date)}>
                  {ago(r.date)}
                </span>
              </div>
              {r.comment && <blockquote className="display mt-3 text-lg leading-snug">“{r.comment}”</blockquote>}
              <figcaption className="mt-3 text-sm text-muted">
                {r.from} · {r.skill}
              </figcaption>
            </figure>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">
          No reviews yet. <Trust value={m.trust} /> is the starting trust for new members.
        </p>
      )}
    </>
  );
}
