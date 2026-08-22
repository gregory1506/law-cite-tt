import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import Card from "./Card.svelte";
import CardChildrenSnippetHarness from "./Card.test.harness.svelte";

describe("Card", () => {
  it("renders its children", () => {
    render(CardChildrenSnippetHarness, { text: "Hello from Card" });

    expect(screen.getByText("Hello from Card")).toBeInTheDocument();
  });

  it("applies the padded class by default and can opt out", () => {
    const { container: withPadding } = render(CardChildrenSnippetHarness, {
      text: "Padded",
    });
    expect(withPadding.querySelector(".card")).toHaveClass("padded");

    const { container: withoutPadding } = render(CardChildrenSnippetHarness, {
      text: "Unpadded",
      padded: false,
    });
    expect(withoutPadding.querySelector(".card")).not.toHaveClass("padded");
  });

  it("accepts a passthrough class", () => {
    const { container } = render(CardChildrenSnippetHarness, {
      text: "Custom class",
      class: "stat-tile",
    });

    expect(container.querySelector(".card")).toHaveClass("stat-tile");
  });
});
