import { useRef, useState } from "react";
import { MessageCircle, Loader2, Send } from "lucide-react";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  provider?: string;
}

interface CompanyChatProps {
  companyId: string;
}

export function CompanyChat({ companyId }: CompanyChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const handleChat = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await api.chatCompany(companyId, q);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, provider: res.provider },
      ]);
      setTimeout(
        () => endRef.current?.scrollIntoView({ behavior: "smooth" }),
        50,
      );
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Eroare la generarea raspunsului. Incearca din nou.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MessageCircle className="w-4 h-4 text-accent-primary" />
        <h3 className="text-sm font-semibold text-gray-400 uppercase">
          Chat cu Compania
        </h3>
        <span className="text-xs text-gray-600 ml-auto">
          Intreaba despre datele din ultimul raport
        </span>
      </div>

      <div className="space-y-3 max-h-80 overflow-y-auto mb-3 pr-1">
        {messages.length === 0 && (
          <p className="text-xs text-gray-600 italic text-center py-6">
            Pune o intrebare despre aceasta companie.
            <br />
            Ex: &ldquo;Care este riscul principal daca dau un credit de 50k
            EUR?&rdquo;
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`rounded-lg px-3 py-2 text-sm max-w-[90%] ${
              msg.role === "user"
                ? "bg-accent-primary/20 text-white ml-auto text-right"
                : "bg-dark-surface text-gray-300"
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.text}</p>
            {msg.provider && msg.role === "assistant" && (
              <p className="text-[10px] text-gray-600 mt-1">
                via {msg.provider}
              </p>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-gray-500 text-xs">
            <Loader2 className="w-3 h-3 animate-spin" />
            Generez raspuns...
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value.slice(0, 500))}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChat()}
          placeholder="Intreaba ceva despre aceasta firma..."
          maxLength={500}
          disabled={loading}
          className="flex-1 bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent-primary disabled:opacity-50"
        />
        <button
          onClick={handleChat}
          disabled={loading || !input.trim()}
          className="btn-primary px-3 py-2 disabled:opacity-50"
          aria-label="Trimite intrebare"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-[10px] text-gray-700 mt-1">
        {input.length}/500 — Enter pentru trimitere | Necesita un raport generat
        anterior
      </p>
    </div>
  );
}
