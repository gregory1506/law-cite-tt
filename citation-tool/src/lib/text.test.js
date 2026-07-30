import { describe, expect, it } from "vitest";
import { excerptAroundQuery, highlightSegments, queryTerms } from "./text.js";

describe("legal text helpers", () => {
  it("normalizes and deduplicates useful query terms", () => {
    expect(queryTerms("the Debtor debtor absconded")).toEqual([
      "the",
      "debtor",
      "absconded",
    ]);
  });

  it("builds a bounded excerpt around the first matching term", () => {
    const text = `${"Opening material ".repeat(50)}absconding debtor${" closing material".repeat(50)}`;
    const excerpt = excerptAroundQuery(text, "absconding debtor", 180);

    expect(excerpt.length).toBeLessThanOrEqual(182);
    expect(excerpt).toContain("absconding debtor");
    expect(excerpt.startsWith("…")).toBe(true);
    expect(excerpt.endsWith("…")).toBe(true);
  });

  it("returns text segments without converting imported markup into HTML", () => {
    const source = '<img src=x onerror="alert(1)"> debtor';
    const segments = highlightSegments(source, "debtor");

    expect(segments.map((segment) => segment.text).join("")).toBe(source);
    expect(segments.at(-1)).toEqual({ text: "debtor", match: true });
  });
});
