import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode, Suspense, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { Layout } from "@/components/Layout";
import { ButtonLink, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth";
import Home from "@/pages/Home";
import "./index.css";

const Explore = lazy(() => import("@/pages/Explore"));
const Matches = lazy(() => import("@/pages/Matches"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Member = lazy(() => import("@/pages/Member"));
const Ledger = lazy(() => import("@/pages/Ledger"));
const Receipt = lazy(() => import("@/pages/Receipt"));
const Insights = lazy(() => import("@/pages/Insights"));
const Auth = lazy(() => import("@/pages/Auth"));

function Private({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner />;
  return me ? children : <Navigate to="/login" replace state={{ from: loc.pathname }} />;
}

const page = (el: ReactNode) => <Suspense fallback={<Spinner />}>{el}</Suspense>;

function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="display text-8xl text-coin-deep">404</p>
      <p className="mt-4 text-ink-2">That page isn't on the ledger.</p>
      <ButtonLink to="/" className="mt-8" variant="outline">
        Back home
      </ButtonLink>
    </div>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "explore", element: page(<Explore />) },
      { path: "matches", element: <Private>{page(<Matches />)}</Private> },
      { path: "me", element: <Private>{page(<Dashboard />)}</Private> },
      { path: "u/:id", element: page(<Member />) },
      { path: "ledger", element: page(<Ledger />) },
      { path: "ledger/:cid", element: page(<Receipt />) },
      { path: "insights", element: page(<Insights />) },
      { path: "login", element: page(<Auth mode="login" />) },
      { path: "signup", element: page(<Auth mode="signup" />) },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      retry: (n, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && n < 2,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster
          position="bottom-right"
          toastOptions={{ className: "!rounded-2xl !border-line !bg-card !text-ink !font-sans", descriptionClassName: "!font-mono !text-muted" }}
        />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
