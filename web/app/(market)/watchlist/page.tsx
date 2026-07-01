/* Watchlist page — /watchlist (docs/08 §8, docs/05, M7).
   Auth-gated: WatchlistClient redirects to /login if not authenticated.
   noindex — personal data, never crawled. */

import type { Metadata } from "next";
import WatchlistClient from "./WatchlistClient";

export const metadata: Metadata = {
  title:  "Watchlist — Saakshya",
  robots: "noindex, nofollow",
};

export default function WatchlistPage() {
  return <WatchlistClient />;
}
