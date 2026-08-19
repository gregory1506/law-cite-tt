import { fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.svelte";

describe("App shell", () => {
  beforeEach(() => {
    localStorage.setItem("lawcite_session_token", "test-session");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      }),
    );
  });

  it("shows Research, Cite, and Chat as primary routes without internal metrics", async () => {
    render(App);

    expect(screen.getByRole("heading", { name: "Research" })).toBeInTheDocument();
    await fireEvent.click(screen.getByRole("button", { name: "Cite" }));
    expect(
      screen.getByRole("heading", { name: "Validate a citation", level: 1 }),
    ).toBeInTheDocument();
    await fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    expect(screen.getByRole("heading", { name: "Chat", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Ask about the Laws of Trinidad and Tobago")).toBeInTheDocument();
    expect(screen.queryByText("Chunks")).not.toBeInTheDocument();
    expect(screen.queryByText("Embedded")).not.toBeInTheDocument();
  });
});
