/**
 * B1: NLQ Ask RIS — Chat panel flotant pentru interogari in limbaj natural.
 * 5 intentii: top_risc, statistici, ultimele, firma_info, comparatie.
 */

import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTIONS = [
  "Care firme au risc ridicat?",
  "Cate analize am facut?",
  "Ce am analizat ultima oara?",
];

export default function AskRIS() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Salut! Sunt asistentul RIS. Poti sa ma intrebi despre:\n• Firme cu risc ridicat\n• Statistici sistem\n• Ultimele analize\n• Detalii despre o firma",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;
    const q = question.trim();
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.askRIS(q);
      setMessages((prev) => [...prev, { role: "assistant", text: res.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Eroare la procesarea intrebarii. Incearca din nou.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <>
      {/* Buton flotant */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-accent-primary hover:bg-accent-glow text-white shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110"
        aria-label="Deschide asistentul RIS"
        title="Intreaba RIS"
      >
        {open ? (
          <X className="w-5 h-5" />
        ) : (
          <MessageCircle className="w-5 h-5" />
        )}
      </button>

      {/* Panel chat */}
      {open && (
        <div className="fixed bottom-20 right-6 z-50 w-80 bg-dark-card border border-dark-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-accent-primary/10 border-b border-dark-border flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-accent-secondary" />
            <span className="text-sm font-semibold text-white">Ask RIS</span>
            <span className="ml-auto text-[10px] text-gray-500">
              AI Assistant
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 max-h-72">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-xl text-xs whitespace-pre-wrap leading-relaxed ${
                    msg.role === "user"
                      ? "bg-accent-primary text-white"
                      : "bg-dark-surface text-gray-200"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-dark-surface px-3 py-2 rounded-xl">
                  <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {messages.length <= 1 && (
            <div className="px-3 pb-2 flex flex-wrap gap-1">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-[10px] px-2 py-1 rounded-full bg-dark-surface border border-dark-border text-gray-400 hover:text-white hover:border-accent-primary/50 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="border-t border-dark-border p-2 flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Intreaba ceva..."
              className="flex-1 bg-dark-surface border border-dark-border rounded-lg px-3 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-accent-primary/50"
              disabled={loading}
              maxLength={500}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-1.5 rounded-lg bg-accent-primary text-white disabled:opacity-40 hover:bg-accent-glow transition-colors"
              aria-label="Trimite intrebarea"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
