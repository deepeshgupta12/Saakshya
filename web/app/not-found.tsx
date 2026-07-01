import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-(--surface-base) text-center px-4">
      <p className="text-5xl font-bold tabular-nums text-(--text-muted)">404</p>
      <p className="text-sm text-(--text-secondary)">This page or symbol could not be found.</p>
      <Link href="/market" className="text-sm text-(--accent) hover:underline">
        Return to market dashboard
      </Link>
    </div>
  );
}
