/* Number, currency, percent, and date formatters — en-IN locale, INR ₹.
   Use these for all financial figures; never inline toLocaleString. */

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const NUM_2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NUM_0 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
const PCT   = new Intl.NumberFormat("en-IN", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: "exceptZero" });

export function formatPrice(v: number | null | undefined): string {
  if (v == null) return "—";
  return INR.format(v);
}

export function formatNumber(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return decimals === 0 ? NUM_0.format(v) : NUM_2.format(v);
}

export function formatPercent(v: number | null | undefined): string {
  if (v == null) return "—";
  return PCT.format(v / 100);
}

export function formatVolume(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1_00_00_000) return `${(v / 1_00_00_000).toFixed(1)}Cr`;
  if (v >= 1_00_000)    return `${(v / 1_00_000).toFixed(1)}L`;
  return NUM_0.format(v);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function signedPercent(v: number | null | undefined): string {
  if (v == null) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}
