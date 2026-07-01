/* Auth layout — centered card, no TopNav/Footer (docs/08 §auth-screens, M7). */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-(--surface-base) flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand mark */}
        <div className="text-center mb-8">
          <span className="text-2xl font-bold tracking-tight text-(--text-primary)">Saakshya</span>
          <p className="text-xs text-(--text-muted) mt-1">Evidence-first Indian equity analytics</p>
        </div>
        {children}
      </div>
    </div>
  );
}
