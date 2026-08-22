import { describe, expect, it } from "vitest";
import { formatDate } from "./date.js";

describe("formatDate", () => {
  it("formats a date with the short month by default", () => {
    expect(formatDate("2012-12-31")).toBe("31 Dec 2012");
  });

  it("formats a date with the long month when requested", () => {
    expect(formatDate("2012-12-31", { month: "long" })).toBe(
      "31 December 2012",
    );
  });

  it("returns the default fallback when no value is given", () => {
    expect(formatDate("")).toBe("Date unavailable");
    expect(formatDate(null)).toBe("Date unavailable");
  });

  it("returns a custom fallback when provided", () => {
    expect(formatDate(undefined, { fallback: "No effective date on file" })).toBe(
      "No effective date on file",
    );
  });
});
