import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import StatusBadgeChildrenSnippetHarness from "./StatusBadge.test.harness.svelte";

describe("StatusBadge", () => {
  it("renders its children", () => {
    render(StatusBadgeChildrenSnippetHarness, { text: "Latest available" });

    expect(screen.getByText("Latest available")).toBeInTheDocument();
  });

  it("defaults to the neutral tone", () => {
    const { container } = render(StatusBadgeChildrenSnippetHarness, {
      text: "Historical version",
    });

    expect(container.querySelector(".badge")).toHaveClass("tone-neutral");
  });

  it("applies the positive tone when requested", () => {
    const { container } = render(StatusBadgeChildrenSnippetHarness, {
      text: "Latest available",
      tone: "positive",
    });

    expect(container.querySelector(".badge")).toHaveClass("tone-positive");
  });
});
