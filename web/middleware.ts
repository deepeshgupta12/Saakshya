/* Middleware — auth gating, admin protection, symbol case normalization.
   docs/06 §2, docs/05 §3. */

import { type NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  /* Admin routes — block at middleware (no auth system yet in Mode A local dev) */
  if (pathname.startsWith("/admin")) {
    return NextResponse.json({ error: "Admin access restricted" }, { status: 403 });
  }

  /* Symbol case normalization: /stocks/tcs → /stocks/TCS (301) */
  const stockMatch = pathname.match(/^\/stocks\/([^/]+)(.*)/);
  if (stockMatch) {
    const sym = stockMatch[1];
    const rest = stockMatch[2] ?? "";
    const upper = sym.toUpperCase();
    if (sym !== upper) {
      const url = request.nextUrl.clone();
      url.pathname = `/stocks/${upper}${rest}`;
      return NextResponse.redirect(url, 301);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/stocks/:symbol*"],
};
