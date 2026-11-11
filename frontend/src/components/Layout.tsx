import clsx from "clsx";
import { LogOut, Menu, Moon, Sun, UserRound, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Avatar, ButtonLink, Coins, Logo } from "./ui";

const LINKS = [
  { to: "/explore", label: "Explore" },
  { to: "/matches", label: "Matches" },
  { to: "/ledger", label: "Ledger" },
  { to: "/insights", label: "Insights" },
];

function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("coinnect.theme", dark ? "dark" : "light");
    } catch {
      /* private mode */
    }
  }, [dark]);
  return (
    <button
      onClick={() => setDark((d) => !d)}
      className="grid size-9 place-items-center rounded-full text-ink-2 transition hover:bg-paper-2 hover:text-ink"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {dark ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />}
    </button>
  );
}

function AccountMenu() {
  const { me, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  if (!me) return null;
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 rounded-full p-0.5 transition hover:bg-paper-2">
        <Avatar name={me.name} id={me.id} size={34} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-60 animate-rise rounded-2xl border border-line bg-card p-2 shadow-xl">
            <div className="px-3 py-2">
              <p className="font-medium">{me.name}</p>
              <p className="truncate text-xs text-muted">{me.email}</p>
            </div>
            <div className="my-1 h-px bg-line" />
            {[
              { to: "/me", label: "Dashboard", icon: <Coins n={me.balance} /> },
              { to: `/u/${me.id}`, label: "Public profile", icon: <UserRound className="size-4" /> },
            ].map((i) => (
              <Link key={i.to} to={i.to} onClick={() => setOpen(false)} className="flex items-center justify-between rounded-xl px-3 py-2 text-sm hover:bg-paper-2">
                {i.label} <span className="text-muted">{i.icon}</span>
              </Link>
            ))}
            <button
              onClick={() => {
                signOut();
                setOpen(false);
                nav("/");
              }}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm text-rust hover:bg-rust-soft"
            >
              Sign out <LogOut className="size-4" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function Layout() {
  const { me } = useAuth();
  const [mobile, setMobile] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    setMobile(false);
    window.scrollTo({ top: 0 });
  }, [loc.pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-paper/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" aria-label="Coinnect home">
            <Logo />
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  clsx("rounded-full px-3.5 py-1.5 text-sm transition", isActive ? "bg-ink text-paper" : "text-ink-2 hover:bg-paper-2 hover:text-ink")
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {me ? (
              <>
                <Link
                  to="/me"
                  className="hidden items-center gap-2 rounded-full border border-line bg-card py-1 pl-1.5 pr-3 text-sm sm:flex"
                  title={me.escrow ? `${me.escrow} more held in escrow` : "Your SkillCoin balance"}
                >
                  <Coins n={me.balance} big className="font-medium" />
                </Link>
                <AccountMenu />
              </>
            ) : (
              <>
                <span className="hidden sm:contents">
                  <ButtonLink to="/login" variant="ghost" size="sm">
                    Sign in
                  </ButtonLink>
                </span>
                <ButtonLink to="/signup" size="sm">
                  Join free
                </ButtonLink>
              </>
            )}
            <button className="grid size-9 place-items-center rounded-full hover:bg-paper-2 md:hidden" onClick={() => setMobile((m) => !m)} aria-label="Menu">
              {mobile ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>
        {mobile && (
          <nav className="grid gap-1 border-t border-line px-4 py-3 md:hidden">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} className="rounded-xl px-3 py-2.5 text-[15px] hover:bg-paper-2">
                {l.label}
              </NavLink>
            ))}
            {me && (
              <NavLink to="/me" className="rounded-xl px-3 py-2.5 text-[15px] hover:bg-paper-2">
                Dashboard
              </NavLink>
            )}
          </nav>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <Logo className="text-ink" />
          <p>Teach an hour, learn an hour. Every session sealed with a verifiable receipt.</p>
          <a href="/docs" className="font-mono text-xs hover:text-ink">
            API docs →
          </a>
        </div>
      </footer>
    </div>
  );
}
