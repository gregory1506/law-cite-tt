import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Cite from "./Cite.svelte";

const foundResponse = {
  status: "found",
  normalized_input: {
    chapter: "8:08",
    section: "12(3)(a)",
    date: "2012-12-31",
  },
  citation: {
    full:
      "Absconding Debtors Act, Chap. 8:08, s. 12(3)(a) (version available as at 31 December 2012)",
    short: "Chap. 8:08, s. 12(3)(a)",
  },
  authority: {
    title: "Absconding Debtors",
    chapter_number: "8:08",
    section_ref: "12(3)(a)",
    heading: "Power to arrest",
    as_at_date: "2009-12-31",
    version_label: "2009 revision",
    download_id: 1001,
    pdf_url: "https://laws.gov.tt/download/1001",
  },
  text: "A debtor may be arrested in the prescribed case.",
  alternatives: [],
};

function response(body, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Server Error",
    json: async () => body,
  });
}

describe("Cite route", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("normalizes fields, renders a found result, and copies both forms", async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes("/api/chapters")) return response([]);
      return response(foundResponse);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(Cite);

    await fireEvent.input(screen.getByLabelText("Chapter"), {
      target: { value: "Chap. 8-8" },
    });
    await fireEvent.input(screen.getByLabelText("Section"), {
      target: { value: "section 12 (3) (A)" },
    });
    await fireEvent.input(screen.getByLabelText(/Available as at/), {
      target: { value: "2012-12-31" },
    });
    await fireEvent.click(screen.getByRole("button", { name: "Validate citation" }));

    expect(await screen.findByText("Citation found")).toBeInTheDocument();
    const requestUrl = fetchMock.mock.calls.find(([url]) =>
      url.includes("/api/citations/resolve"),
    )[0];
    expect(requestUrl).toContain("chapter=8%3A08");
    expect(requestUrl).toContain("section=12%283%29%28a%29");
    expect(screen.getByText(foundResponse.citation.full)).toBeInTheDocument();
    expect(screen.getByText(foundResponse.citation.short)).toBeInTheDocument();
    expect(screen.getByText("Available as at 31 December 2012")).toBeInTheDocument();
    expect(screen.queryByText(/^Current$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^In force$/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/does not claim that a provision is currently in force/i),
    ).toBeInTheDocument();

    await fireEvent.click(screen.getByRole("button", { name: "Copy full citation" }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      foundResponse.citation.full,
    );
    expect(await screen.findByText("Full citation copied")).toBeInTheDocument();

    await fireEvent.click(screen.getByRole("button", { name: "Copy short citation" }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      foundResponse.citation.short,
    );
  });

  it.each([
    ["not_found", "Citation not found"],
    ["ambiguous", "Citation ambiguous"],
  ])("renders the explicit %s state", async (status, label) => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        url.includes("/api/chapters")
          ? response([])
          : response({
              status,
              normalized_input: { chapter: "8:08", section: "99", date: null },
              citation: null,
              authority: null,
              text: "",
              alternatives: [],
            }),
      ),
    );
    render(Cite);

    await fireEvent.input(screen.getByLabelText("Chapter"), {
      target: { value: "8:08" },
    });
    await fireEvent.input(screen.getByLabelText("Section"), {
      target: { value: "99" },
    });
    await fireEvent.click(screen.getByRole("button", { name: "Validate citation" }));

    expect(await screen.findByText(label)).toBeInTheDocument();
  });

  it("submits with Enter and renders API errors accessibly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        url.includes("/api/chapters") ? response([]) : response({}, false),
      ),
    );
    render(Cite);

    await fireEvent.input(screen.getByLabelText("Chapter"), {
      target: { value: "8:08" },
    });
    const sectionInput = screen.getByLabelText("Section");
    await fireEvent.input(sectionInput, { target: { value: "12" } });
    await fireEvent.keyDown(sectionInput, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Citation check unavailable",
      ),
    );
  });
});
