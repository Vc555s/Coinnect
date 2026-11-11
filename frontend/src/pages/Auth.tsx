import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button, Coins, ErrorNote } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const DEMO = { email: "asha@coinnect.dev", password: "demo1234" };

export default function Auth({ mode }: { mode: "login" | "signup" }) {
  const { signIn, signUp } = useAuth();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? (mode === "signup" ? "/me" : "/me");
  const [form, setForm] = useState({ name: "", email: "", password: "", headline: "" });
  const go = useMutation({
    mutationFn: (creds?: typeof DEMO) =>
      creds ? signIn(creds.email, creds.password) : mode === "login" ? signIn(form.email, form.password) : signUp(form),
    onSuccess: () => nav(from, { replace: true }),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    go.mutate(undefined);
  };
  const bind = (k: keyof typeof form) => ({ value: form[k], onChange: (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value })) });

  return (
    <div className="mx-auto grid max-w-5xl overflow-hidden rounded-[2rem] border border-line bg-card md:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-ink p-10 text-paper md:block">
        <div className="absolute -bottom-20 -left-20 size-72 rounded-full border-[24px] border-coin/80" aria-hidden />
        <div className="absolute -bottom-32 left-24 size-72 rounded-full border-[24px] border-paper/10" aria-hidden />
        <p className="eyebrow !text-paper/50">Coinnect</p>
        <h2 className="display relative mt-6 text-4xl leading-tight">
          {mode === "signup" ? "Your knowledge is worth something here." : "Welcome back to the exchange."}
        </h2>
        <ul className="relative mt-8 space-y-3 text-sm text-paper/75">
          <li className="flex items-center gap-2">
            <Coins n={10} /> starting balance for every new member
          </li>
          <li>• Coins held in escrow until a session really happens</li>
          <li>• A tamper-evident receipt for every exchange</li>
        </ul>
      </div>

      <div className="p-8 sm:p-12">
        <h1 className="display text-4xl">{mode === "login" ? "Sign in" : "Create your account"}</h1>
        <p className="mt-2 text-sm text-muted">
          {mode === "login" ? "New here? " : "Already a member? "}
          <Link to={mode === "login" ? "/signup" : "/login"} state={{ from }} className="font-medium text-ink underline">
            {mode === "login" ? "Create an account" : "Sign in"}
          </Link>
        </p>

        <form onSubmit={submit} className="mt-8 grid gap-4">
          {mode === "signup" && (
            <>
              <div>
                <label className="label" htmlFor="name">
                  Name
                </label>
                <input id="name" className="input" required minLength={2} autoComplete="name" {...bind("name")} />
              </div>
              <div>
                <label className="label" htmlFor="headline">
                  Headline <span className="font-normal text-muted">(optional)</span>
                </label>
                <input id="headline" className="input" maxLength={140} placeholder="e.g. Pianist who wants to learn to code" {...bind("headline")} />
              </div>
            </>
          )}
          <div>
            <label className="label" htmlFor="email">
              Email
            </label>
            <input id="email" type="email" className="input" required autoComplete="email" {...bind("email")} />
          </div>
          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              required
              minLength={mode === "signup" ? 8 : 1}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              {...bind("password")}
            />
            {mode === "signup" && <p className="mt-1 text-xs text-muted">At least 8 characters.</p>}
          </div>
          {go.error && <ErrorNote error={go.error} />}
          <Button size="lg" loading={go.isPending && !go.variables}>
            {mode === "login" ? "Sign in" : "Create account"} <ArrowRight className="size-4" />
          </Button>
        </form>

        <div className="mt-8 rounded-2xl border border-dashed border-line p-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <Sparkles className="size-4 text-coin" /> Just looking around?
          </p>
          <p className="mt-1 text-xs text-muted">
            Sign in as Asha, a demo member with a full history and a request waiting in her inbox. All demo accounts use the password{" "}
            <code className="font-mono">demo1234</code>.
          </p>
          <Button size="sm" variant="outline" className="mt-3" onClick={() => go.mutate(DEMO)} loading={go.isPending && !!go.variables}>
            Use the demo account
          </Button>
        </div>
      </div>
    </div>
  );
}
