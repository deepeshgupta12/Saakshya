import type { Metadata } from "next";

import { Landing } from "@/components/marketing/Landing";

export const metadata: Metadata = {
  title: "Saakshya — Evidence-first Indian equity analytics",
  description:
    "Validated NSE/BSE scanners, sector strength and AI explanations you can trace — evidence-first, dark-first. Not investment advice.",
  robots: { index: true, follow: true },
};

export default function HomePage() {
  return <Landing />;
}
