import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { AuthGate } from "@/components/auth/AuthGate";

/**
 * (app) — the authenticated app shell (docs/06 §1). Same chrome as (market) but the
 * content is wrapped in AuthGate, so portfolio / strategy / watchlist require a session.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-(--surface-base)">
      <TopNav />
      <main id="main-content" className="flex-1 mx-auto w-full max-w-[1440px] px-4 py-8">
        <AuthGate>{children}</AuthGate>
      </main>
      <Footer />
    </div>
  );
}
