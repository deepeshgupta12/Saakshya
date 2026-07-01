import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";

export default function MarketLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-(--surface-base)">
      <TopNav />
      <main id="main-content" className="flex-1 mx-auto w-full max-w-[1440px] px-4 py-8">
        {children}
      </main>
      <Footer />
    </div>
  );
}
