/** Presentation formatting for backend-provided metrics. No business logic here. */

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

export function formatChange(changePct: number | null): string {
  if (changePct === null) return "n/a";
  const sign = changePct > 0 ? "+" : "";
  return `${sign}${changePct.toFixed(1)}%`;
}

export function formatBucketLabel(periodStart: string): string {
  const date = new Date(periodStart);
  if (Number.isNaN(date.getTime())) return periodStart;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}`;
}

export function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

export function formatProbability(probability: number): string {
  return `${(probability * 100).toFixed(1)}%`;
}

export function formatDate(value: string | null): string {
  if (value === null) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDays(value: number | null, singular: string, plural: string): string {
  if (value === null) return "—";
  if (value === 1) return `1 ${singular}`;
  return `${formatNumber(value)} ${plural}`;
}
