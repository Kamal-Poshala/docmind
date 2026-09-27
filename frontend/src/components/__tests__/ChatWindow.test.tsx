import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatWindow } from "@/components/ChatWindow";
import { streamChat } from "@/lib/api";

vi.mock("@/lib/api", () => ({ streamChat: vi.fn() }));

const mockedStreamChat = vi.mocked(streamChat);

beforeEach(() => {
  mockedStreamChat.mockReset();
});

async function sendMessage(text: string) {
  await userEvent.type(screen.getByPlaceholderText(/ask something/i), text);
  await userEvent.click(screen.getByRole("button", { name: /send/i }));
}

describe("ChatWindow", () => {
  it("shows a hint before any messages are sent", () => {
    render(<ChatWindow />);

    expect(screen.getByText(/upload a document, then ask/i)).toBeInTheDocument();
  });

  it("streams the assistant reply token by token and clears the input", async () => {
    mockedStreamChat.mockImplementation(async (_message, _history, onToken) => {
      onToken("Hel");
      onToken("lo");
    });

    render(<ChatWindow />);
    await sendMessage("hi there");

    expect(screen.getByText("hi there")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Hello")).toBeInTheDocument());
    expect(screen.getByPlaceholderText(/ask something/i)).toHaveValue("");
    expect(mockedStreamChat).toHaveBeenCalledWith("hi there", [], expect.any(Function));
  });

  it("shows the thrown error message instead of a raw failure", async () => {
    mockedStreamChat.mockRejectedValue(new Error("LLM_API_KEY is not set (LLM_PROVIDER=gemini)."));

    render(<ChatWindow />);
    await sendMessage("hi");

    await waitFor(() =>
      expect(screen.getByText(/LLM_API_KEY is not set/)).toBeInTheDocument(),
    );
  });

  it("falls back to a network message for a bare TypeError", async () => {
    mockedStreamChat.mockRejectedValue(new TypeError("Failed to fetch"));

    render(<ChatWindow />);
    await sendMessage("hi");

    await waitFor(() =>
      expect(screen.getByText(/could not reach the backend/i)).toBeInTheDocument(),
    );
  });

  it("does not submit an empty or whitespace-only message", async () => {
    render(<ChatWindow />);

    await userEvent.type(screen.getByPlaceholderText(/ask something/i), "   ");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(mockedStreamChat).not.toHaveBeenCalled();
  });
});
