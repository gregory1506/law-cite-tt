import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChatDock from "./ChatDock.svelte";
import { chatState, clearChat } from "../../lib/chat.svelte.js";

function response(body, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? "OK" : "Server Error",
    json: async () => body,
  });
}

const grounded = {
  status: "ok",
  answer: "Section 4 of the Absconding Debtors Act allows arrest in the prescribed case.",
  sources: [
    {
      id: "chunk:42",
      title: "Absconding Debtors",
      chapter: "8:08",
      section: "4",
      date: "2009-12-31",
      url: "https://laws.gov.tt/ttdll-web/revision/download/105522?type=act",
    },
  ],
};

const refused = {
  status: "refused",
  answer: "I could not verify that answer against the Laws of Trinidad and Tobago.",
  sources: [],
};

async function send(text) {
  const input = screen.getByLabelText("Message");
  await fireEvent.input(input, { target: { value: text } });
  await fireEvent.click(screen.getByLabelText("Send message"));
}

describe("ChatDock", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
    clearChat();
    chatState.open = true;
    chatState.input = "";
    chatState.error = "";
  });

  it("sends the message and renders the grounded answer with its source", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(grounded));
    vi.stubGlobal("fetch", fetchMock);
    render(ChatDock);

    await send("What does s. 4 say?");

    await waitFor(() => {
      expect(screen.getByText("What does s. 4 say?")).toBeTruthy();
    });
    expect(screen.getByText(/prescribed case/)).toBeTruthy();
    expect(screen.getByText("8:08 · s. 4")).toBeTruthy();
    expect(screen.getByText("Official PDF")).toBeTruthy();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url.endsWith("/api/chat")).toBe(true);
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body);
    expect(body.messages[0]).toEqual({ role: "user", content: "What does s. 4 say?" });
    expect(body.mode).toBe("research");
  });

  it("shows a not-verified banner for refused answers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(refused)));
    render(ChatDock);

    await send("What does s. 4 say?");

    await waitFor(() => {
      expect(screen.getByText("Not verified")).toBeTruthy();
    });
    expect(screen.getByText(/I could not verify/)).toBeTruthy();
  });

  it("shows an explicit card when the assistant is unconfigured", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response({ status: "unconfigured", answer: "", sources: [] }),
      ),
    );
    render(ChatDock);

    await send("Anything?");

    await waitFor(() => {
      expect(screen.getByText("Assistant not configured")).toBeTruthy();
    });
  });

  it("sends the selected mode", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(grounded));
    vi.stubGlobal("fetch", fetchMock);
    render(ChatDock);

    await fireEvent.click(screen.getByRole("button", { name: "Precedent" }));
    await send("Which cases cite this?");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.mode).toBe("precedent");
  });

  it("surfaces a request failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({}, false)));
    render(ChatDock);

    await send("What does s. 4 say?");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });
});
