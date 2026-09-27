import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentPanel } from "@/components/DocumentPanel";
import { deleteDocument, listDocuments, uploadDocument } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

const mockedList = vi.mocked(listDocuments);
const mockedUpload = vi.mocked(uploadDocument);
const mockedDelete = vi.mocked(deleteDocument);

const doc = { id: "1", filename: "handbook.pdf", created_at: "2026-01-01" };

beforeEach(() => {
  mockedList.mockReset();
  mockedUpload.mockReset();
  mockedDelete.mockReset();
});

describe("DocumentPanel", () => {
  it("lists documents returned on mount", async () => {
    mockedList.mockResolvedValue([doc]);

    render(<DocumentPanel />);

    expect(await screen.findByText("handbook.pdf")).toBeInTheDocument();
  });

  it("shows an empty state when there are no documents", async () => {
    mockedList.mockResolvedValue([]);

    render(<DocumentPanel />);

    expect(await screen.findByText(/no documents yet/i)).toBeInTheDocument();
  });

  it("shows an error message when loading documents fails", async () => {
    mockedList.mockRejectedValue(new Error("network down"));

    render(<DocumentPanel />);

    expect(await screen.findByText(/could not load documents/i)).toBeInTheDocument();
  });

  it("uploads a selected file and refreshes the list", async () => {
    mockedList.mockResolvedValueOnce([]).mockResolvedValueOnce([doc]);
    mockedUpload.mockResolvedValue(doc);

    render(<DocumentPanel />);
    await screen.findByText(/no documents yet/i);

    const file = new File(["hello"], "handbook.pdf", { type: "text/plain" });
    await userEvent.upload(screen.getByLabelText(/upload pdf or text file/i), file);

    await waitFor(() => expect(mockedUpload).toHaveBeenCalledWith(file));
    expect(await screen.findByText("handbook.pdf")).toBeInTheDocument();
    expect(mockedList).toHaveBeenCalledTimes(2);
  });

  it("shows the upload error and still re-enables the input", async () => {
    mockedList.mockResolvedValue([]);
    mockedUpload.mockRejectedValue(new Error("No extractable text found in file"));

    render(<DocumentPanel />);
    await screen.findByText(/no documents yet/i);

    const file = new File([""], "empty.pdf");
    await userEvent.upload(screen.getByLabelText(/upload pdf or text file/i), file);

    expect(await screen.findByText(/no extractable text found/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/upload pdf or text file/i)).not.toBeDisabled();
  });

  it("deletes a document and refreshes the list", async () => {
    mockedList.mockResolvedValueOnce([doc]).mockResolvedValueOnce([]);
    mockedDelete.mockResolvedValue(undefined);

    render(<DocumentPanel />);
    await screen.findByText("handbook.pdf");

    await userEvent.click(screen.getByRole("button", { name: /delete handbook.pdf/i }));

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith("1"));
    await waitFor(() => expect(screen.getByText(/no documents yet/i)).toBeInTheDocument());
  });
});
