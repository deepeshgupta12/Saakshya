import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "@/components/layout/Providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

/* JetBrains Mono — all prices, scores, and numeric metrics per docs/07 §1.4 */
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono-code",
  display: "swap",
});

export const metadata: Metadata = {
  title:       "Saakshya — Indian Equity Analytics",
  description: "Evidence-first equity scanner, market intelligence and analytics for NSE/BSE. Not investment advice.",
  robots:      { index: true, follow: true },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  /* Read theme cookie server-side to avoid flash — docs/07 §4 */
  const cookieStore = await cookies();
  const theme = cookieStore.get("saakshya-theme")?.value === "light" ? "light" : "dark";

  return (
    <html lang="en" data-theme={theme} className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
