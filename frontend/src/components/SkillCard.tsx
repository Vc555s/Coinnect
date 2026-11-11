import { ArrowUpRight, CalendarClock } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Skill } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { RequestDialog } from "./RequestDialog";
import { Avatar, Button, ButtonLink, Coins, Trust } from "./ui";

const CATEGORY_TINT: Record<string, string> = {
  Tech: "oklch(0.72 0.1 250)",
  Design: "oklch(0.72 0.13 330)",
  Languages: "oklch(0.74 0.11 160)",
  Music: "oklch(0.72 0.12 20)",
  Business: "oklch(0.72 0.08 80)",
  Science: "oklch(0.72 0.1 200)",
  Craft: "oklch(0.74 0.12 50)",
  Wellness: "oklch(0.74 0.1 130)",
  Other: "oklch(0.7 0.02 80)",
};

export function CategoryDot({ category }: { category: string }) {
  return <span className="inline-block size-2 rounded-full" style={{ background: CATEGORY_TINT[category] ?? CATEGORY_TINT.Other }} />;
}

export function SkillCard({ skill, score, delay = 0 }: { skill: Skill; score?: number; delay?: number }) {
  const { me } = useAuth();
  const [open, setOpen] = useState(false);
  const mine = me?.id === skill.owner.id;
  const offer = skill.kind === "offer";

  return (
    <article
      className="card group flex animate-rise flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-2/40 hover:shadow-[0_18px_40px_-24px_rgba(22,20,15,.35)]"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mb-4 flex items-center justify-between gap-2 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <CategoryDot category={skill.category} /> {skill.category}
          {offer && <span className="before:mx-1.5 before:content-['·']">{skill.level}</span>}
        </span>
        {score !== undefined && <span className="font-mono text-[11px] text-verdigris">{Math.round(score * 100)}% match</span>}
      </div>

      <h3 className="display text-[22px] leading-tight">{skill.name}</h3>
      {skill.description ? (
        <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-2">{skill.description}</p>
      ) : (
        !offer && <p className="mt-2 text-sm text-muted">Looking for someone to teach this.</p>
      )}

      <div className="mt-auto pt-5">
        <Link to={`/u/${skill.owner.id}`} className="flex items-center gap-3 rounded-xl py-1 transition hover:opacity-80">
          <Avatar name={skill.owner.name} id={skill.owner.id} size={32} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{skill.owner.name}</p>
            <Trust value={skill.owner.trust} count={skill.owner.ratings} />
          </div>
        </Link>

        <div className="mt-4 flex items-center justify-between gap-3 border-t border-dashed border-line pt-4">
          {offer ? (
            <>
              <div className="min-w-0 text-xs text-muted">
                <p>
                  <Coins n={skill.rate} className="text-sm font-medium text-ink" /> per session
                </p>
                <p className="mt-1 flex items-center gap-1 truncate">
                  <CalendarClock className="size-3" />
                  {skill.availability}
                </p>
              </div>
              {mine ? (
                <span className="chip">Your offer</span>
              ) : me ? (
                <Button size="sm" variant="coin" onClick={() => setOpen(true)}>
                  Book
                </Button>
              ) : (
                <ButtonLink size="sm" variant="outline" to="/login" state={{ from: "/explore" }}>
                  Sign in
                </ButtonLink>
              )}
            </>
          ) : (
            <>
              <span className="text-xs text-muted">Wants to learn</span>
              <ButtonLink size="sm" variant="outline" to={`/u/${skill.owner.id}`}>
                View profile <ArrowUpRight className="size-3.5" />
              </ButtonLink>
            </>
          )}
        </div>
      </div>
      {offer && <RequestDialog skill={skill} open={open} onClose={() => setOpen(false)} />}
    </article>
  );
}
