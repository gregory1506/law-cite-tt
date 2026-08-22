export function formatDate(value, { fallback = "Date unavailable", month = "short" } = {}) {
  if (!value) return fallback;
  return new Intl.DateTimeFormat("en-TT", {
    year: "numeric",
    month,
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
