import { keepPreviousData, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Search, SearchX } from "lucide-react";
import { useDeferredValue } from "react";
import { useSearchParams } from "react-router-dom";
import { SkillCard } from "@/components/SkillCard";
import { Empty, ErrorNote, PageHeader, Segmented, Spinner } from "@/components/ui";
import { api, type Skill, type SkillKind } from "@/lib/api";

const SORTS = [
  { value: "relevance", label: "Best match" },
  { value: "trust", label: "Most trusted" },
  { value: "rate", label: "Lowest price" },
  { value: "newest", label: "Newest" },
];

export default function Explore() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const kind = (params.get("kind") as SkillKind) ?? "offer";
  const category = params.get("category") ?? "All";
  const sort = params.get("sort") ?? "relevance";
  const deferredQ = useDeferredValue(q);

  const set = (key: string, value: string, fallback: string) => {
    const next = new URLSearchParams(params);
    if (value === fallback) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  const cats = useQuery({ queryKey: ["categories"], queryFn: () => api<string[]>("/api/skills/categories"), staleTime: Infinity });
  const skills = useQuery({
    queryKey: ["skills", deferredQ, kind, category, sort],
    queryFn: () =>
      api<Skill[]>(
        `/api/skills?${new URLSearchParams({ q: deferredQ, kind, sort, ...(category !== "All" ? { category } : {}) })}`,
      ),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader eyebrow="Explore" title={kind === "offer" ? "Skills on offer" : "What people want to learn"}>
        {kind === "offer"
          ? "Book a session with coins held in escrow until you confirm it happened."
          : "Wishlists from the community. Teach one of these to earn coins."}
      </PageHeader>

      <div className="sticky top-16 z-20 -mx-4 mb-8 border-b border-line/70 bg-paper/85 px-4 py-4 backdrop-blur-xl sm:-mx-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-[240px] flex-1 items-center gap-2 rounded-full border border-line bg-card px-4 focus-within:border-coin">
            <Search className="size-4 text-muted" />
            <input
              value={q}
              onChange={(e) => set("q", e.target.value, "")}
              placeholder="Search skills — try “js” or “paint”"
              className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-muted"
            />
          </label>
          <Segmented
            value={kind}
            onChange={(v) => set("kind", v, "offer")}
            options={[
              { value: "offer", label: "Offered" },
              { value: "request", label: "Wanted" },
            ]}
          />
          <select value={sort} onChange={(e) => set("sort", e.target.value, "relevance")} className="input !w-auto !rounded-full !py-2">
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
          {["All", ...(cats.data ?? [])].map((c) => (
            <button
              key={c}
              onClick={() => set("category", c, "All")}
              className={clsx(
                "shrink-0 rounded-full border px-3.5 py-1 text-sm transition",
                category === c ? "border-ink bg-ink text-paper" : "border-line text-ink-2 hover:border-ink-2",
              )}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {skills.isLoading ? (
        <Spinner label="Finding skills" />
      ) : skills.error ? (
        <ErrorNote error={skills.error} />
      ) : !skills.data?.length ? (
        <Empty icon={<SearchX className="size-5" />} title="Nothing here yet">
          No {kind === "offer" ? "offers" : "requests"} match{q && ` “${q}”`}. Try a broader word, or switch to{" "}
          {kind === "offer" ? "Wanted" : "Offered"}.
        </Empty>
      ) : (
        <>
          <p className="mb-4 text-sm text-muted">
            {skills.data.length} {skills.data.length === 1 ? "result" : "results"}
            {skills.isFetching && " · updating…"}
          </p>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {skills.data.map((s, i) => (
              <SkillCard key={s.id} skill={s} delay={Math.min(i, 8) * 40} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
