import { useState } from "react";
import { Send, Loader2, Sparkles } from "lucide-react";
import clsx from "clsx";

interface ParseResult {
  analysis_type: string;
  input_params: Record<string, string>;
  confidence: number;
  suggestion: string;
}

interface ChatInputProps {
  onParsed: (result: ParseResult) => void;
}

export default function ChatInput({ onParsed }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ParseResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/analysis/parse-query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });
      const data: ParseResult = await res.json();
      setResult(data);
    } catch {
      console.warn("Failed to parse AI query");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="w-4 h-4 text-accent-secondary" />
        <span className="text-sm font-medium text-gray-300">
          Descrie ce vrei sa analizezi
        </span>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          className="input-field flex-1"
          placeholder='Ex: "Verifica firma Bitdefender SRL, CUI 18189442, risc partener"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="btn-primary flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>

      {result && (
        <div className="p-3 bg-dark-surface rounded-lg border border-dark-border">
          <p className="text-sm text-accent-light">{result.suggestion}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>
              Incredere: {Math.round(result.confidence * 100)}%
            </span>
            {result.input_params.cui && (
              <span>CUI: {result.input_params.cui}</span>
            )}
          </div>
          <button
            className="btn-primary mt-3 text-sm"
            onClick={() => onParsed(result)}
          >
            Continua cu aceasta analiza
          </button>
        </div>
      )}
    </div>
  );
}
