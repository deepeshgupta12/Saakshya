"use client";
export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-(--surface-base) text-center px-4">
      <p className="text-sm font-medium text-(--bearish)">An unexpected error occurred.</p>
      <button
        type="button"
        onClick={reset}
        className="text-sm text-(--accent) hover:underline"
      >
        Try again
      </button>
    </div>
  );
}
