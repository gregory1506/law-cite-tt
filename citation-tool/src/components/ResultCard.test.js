import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import ResultCard from "./ResultCard.svelte";

const item = {
  key: "9:70::244",
  title: "Bankruptcy and Insolvency",
  chapter_number: "9:70",
  section_ref: "244",
  heading: "Summary administration",
  matched_version: {
    version_id: 2,
    download_id: 1002,
    as_at_date: "2012-12-31",
    version_label: "2012 revision",
    chunk_id: 8,
    chunk_text:
      '<img src=x onerror="alert(1)"> ' +
      "The debtor has absconded. ".repeat(40),
    pdf_url: "https://laws.gov.tt/example.pdf",
  },
  latest_available: {
    version_id: 2,
    download_id: 1002,
    as_at_date: "2012-12-31",
    version_label: "2012 revision",
    pdf_url: "https://laws.gov.tt/example.pdf",
  },
  versions: [
    {
      version_id: 2,
      download_id: 1002,
      as_at_date: "2012-12-31",
      version_label: "2012 revision",
      pdf_url: "https://laws.gov.tt/example.pdf",
    },
  ],
  score: 0.9876,
};

describe("ResultCard", () => {
  it("renders legal authority metadata without exposing scores or raw HTML", () => {
    const { container } = render(ResultCard, {
      item,
      query: "absconded debtor",
    });

    expect(screen.getByText("Bankruptcy and Insolvency")).toBeInTheDocument();
    expect(screen.getByText("Chap. 9:70")).toBeInTheDocument();
    expect(screen.getByText("Section 244")).toBeInTheDocument();
    expect(screen.getByText("Latest available")).toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(container.querySelector("img")).not.toBeInTheDocument();
    expect(screen.getByText(/<img src=x onerror=/)).toBeInTheDocument();
  });

  it("expands and collapses long provision text explicitly", async () => {
    render(ResultCard, { item, query: "debtor" });

    const expand = screen.getByRole("button", { name: "Read provision" });
    expect(expand).toHaveAttribute("aria-expanded", "false");
    await fireEvent.click(expand);

    const collapse = screen.getByRole("button", { name: "Show excerpt" });
    expect(collapse).toHaveAttribute("aria-expanded", "true");
  });
});
