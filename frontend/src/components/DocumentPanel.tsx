"use client";

import { useEffect, useRef, useState } from "react";
import { DocumentSummary, deleteDocument, listDocuments, uploadDocument } from "@/lib/api";

export function DocumentPanel() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = () => {
    listDocuments()
      .then(setDocuments)
      .catch(() => setError("Could not load documents"));
  };

  useEffect(refresh, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(file);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    await deleteDocument(id);
    refresh();
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div>
        <h2 className="text-sm font-semibold text-foreground/70 uppercase tracking-wide">
          Documents
        </h2>
        <label className="mt-3 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-foreground/20 px-3 py-4 text-sm text-foreground/60 transition hover:border-foreground/40 hover:text-foreground">
          {uploading ? "Uploading…" : "Upload PDF or text file"}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
            disabled={uploading}
          />
        </label>
        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      </div>

      <ul className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {documents.length === 0 && (
          <li className="text-sm text-foreground/40">No documents yet.</li>
        )}
        {documents.map((doc) => (
          <li
            key={doc.id}
            className="flex items-center justify-between gap-2 rounded-md bg-foreground/5 px-3 py-2 text-sm"
          >
            <span className="truncate" title={doc.filename}>
              {doc.filename}
            </span>
            <button
              onClick={() => handleDelete(doc.id)}
              className="text-foreground/40 hover:text-red-500"
              aria-label={`Delete ${doc.filename}`}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
