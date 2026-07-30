import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import SearchBar from "./SearchBar.svelte";

describe("SearchBar", () => {
  it("uses legal-task labels while preserving API mode values", async () => {
    const onSearch = vi.fn();
    render(SearchBar, { chapters: [], onSearch });

    expect(screen.getByRole("option", { name: "Exact wording" })).toHaveValue("fts");
    expect(screen.getByRole("option", { name: "Best match" })).toHaveValue("hybrid");
    expect(screen.getByRole("option", { name: "Related concepts" })).toHaveValue("vector");

    await fireEvent.input(screen.getByRole("searchbox"), {
      target: { value: "absconding debtor" },
    });
    await fireEvent.change(screen.getByLabelText("Search method"), {
      target: { value: "vector" },
    });
    await fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).toHaveBeenCalledWith({
      query: "absconding debtor",
      mode: "vector",
      chapter: "",
      date: "",
    });
  });

  it("clears the query, active filters, and parent result state", async () => {
    const onClear = vi.fn();
    render(SearchBar, {
      chapters: [],
      onSearch: vi.fn(),
      onClear,
      query: "absconding debtor",
      chapter: "8:08",
      date: "2016-12-31",
    });

    await fireEvent.click(
      screen.getByRole("button", { name: "Clear search" }),
    );

    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.getByLabelText("Chapter")).toHaveValue("");
    expect(screen.getByLabelText("Available as at")).toHaveValue("");
    expect(onClear).toHaveBeenCalledOnce();
  });
});
