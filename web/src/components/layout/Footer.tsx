import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[--border-subtle] bg-[--surface-base] px-4 py-6 mt-auto">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <p className="text-xs text-[--text-muted]">
          © {new Date().getFullYear()} Saakshya. Analytics and evidence only — not investment advice.
        </p>
        <nav className="flex gap-4 text-xs" aria-label="Footer navigation">
          <Link href="/legal/terms"   className="text-[--text-muted] hover:text-[--text-secondary]">Terms</Link>
          <Link href="/legal/privacy" className="text-[--text-muted] hover:text-[--text-secondary]">Privacy</Link>
          <Link href="/legal/disclaimer" className="text-[--text-muted] hover:text-[--text-secondary]">Disclaimer</Link>
        </nav>
      </div>
    </footer>
  );
}
