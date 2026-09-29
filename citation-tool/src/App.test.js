import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.svelte";

describe("App shell", () => {
  beforeEach(() => {
    localStorage.setItem("lawcite_session_token", "test-session");
    window.history.replaceState(null, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      }),
    );
  });

  it("shows Research and Cite as primary routes, chat as a floating dock", async () => {
    render(App);

    expect(screen.getByRole("heading", { name: "Research" })).toBeInTheDocument();
    await fireEvent.click(screen.getByRole("button", { name: "Cite" }));
    expect(
      screen.getByRole("heading", { name: "Validate a citation", level: 1 }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/cite");

    expect(
      screen.queryByRole("button", { name: "Chat" }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Open research assistant")).toBeInTheDocument();
    expect(document.getElementById("chat-dock")).toBeTruthy();
    expect(screen.queryByText("Chunks")).not.toBeInTheDocument();
    expect(screen.queryByText("Embedded")).not.toBeInTheDocument();
  });

  it("returns to Research from the sidebar and resets the tab in the URL", async () => {
    window.history.replaceState(null, "", "/cite");
    render(App);

    expect(
      screen.getByRole("heading", { name: "Validate a citation", level: 1 }),
    ).toBeInTheDocument();
    const nav = within(document.getElementById("primary-navigation"));
    await fireEvent.click(nav.getByRole("button", { name: "Research" }));
    expect(screen.getByRole("heading", { name: "Research", level: 1 })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });
});
