import { ChatWindow } from "@/components/ChatWindow";
import { DocumentPanel } from "@/components/DocumentPanel";

export default function Home() {
  return (
    <div className="flex flex-1">
      <aside className="w-72 border-r border-foreground/10">
        <DocumentPanel />
      </aside>
      <main className="flex flex-1 flex-col">
        <header className="border-b border-foreground/10 px-6 py-4">
          <h1 className="text-lg font-semibold">DocMind</h1>
          <p className="text-xs text-foreground/50">
            Ask questions grounded in your uploaded documents.
          </p>
        </header>
        <ChatWindow />
      </main>
    </div>
  );
}
