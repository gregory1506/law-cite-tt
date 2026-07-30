export function queryTerms(query) {
  return [...new Set(
    query
      .trim()
      .split(/\s+/)
      .map((term) => term.toLowerCase())
      .filter((term) => term.length > 2),
  )];
}

export function excerptAroundQuery(text, query, maxLength = 620) {
  const value = String(text || "").trim();
  if (value.length <= maxLength) return value;

  const lower = value.toLowerCase();
  const positions = queryTerms(query)
    .map((term) => lower.indexOf(term))
    .filter((index) => index >= 0);
  const matchAt = positions.length ? Math.min(...positions) : 0;
  let start = Math.max(0, matchAt - Math.floor(maxLength * 0.25));
  let end = Math.min(value.length, start + maxLength);

  if (start > 0) {
    const nextSpace = value.indexOf(" ", start);
    start = nextSpace >= 0 && nextSpace < end ? nextSpace + 1 : start;
  }
  if (end < value.length) {
    const previousSpace = value.lastIndexOf(" ", end);
    end = previousSpace > start ? previousSpace : end;
  }

  return `${start > 0 ? "…" : ""}${value.slice(start, end).trim()}${
    end < value.length ? "…" : ""
  }`;
}

export function highlightSegments(text, query) {
  const terms = queryTerms(query);
  if (!terms.length) return [{ text: String(text || ""), match: false }];

  const escaped = terms.map((term) =>
    term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const matcher = new RegExp(`(${escaped.join("|")})`, "gi");
  const termSet = new Set(terms);

  return String(text || "")
    .split(matcher)
    .filter(Boolean)
    .map((part) => ({
      text: part,
      match: termSet.has(part.toLowerCase()),
    }));
}
