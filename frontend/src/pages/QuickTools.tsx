import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Calculator,
  Loader2,
  Building2,
  ChevronRight,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useDebounce } from "@/hooks/useDebounce";

// Tipuri derivate din semnaturile API (DRY + strict, fara `any`)
type FtsResult = Awaited<ReturnType<typeof api.searchFts>>[number];
type QuickScoreResponse = Awaited<ReturnType<typeof api.quickScore>>;
type QuickScoreRow = QuickScoreResponse["results"][number];

const MAX_CUIS = 20;

// Formatare cifra de afaceri (RON) cu fallback pentru valori lipsa
const formatCA = (value: number | null | undefined): string =>
  value == null ? "-" : value.toLocaleString("ro-RO");

// Clase culori in functie de campul `risk` (Verde/Galben/Rosu), fallback gri
const RISK_CLASSES: Record<string, string> = {
  Verde: "bg-green-500/20 text-green-400 border-green-500/30",
  Galben: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Rosu: "bg-red-500/20 text-red-400 border-red-500/30",
};

const scoreBadge = (score: number | undefined, risk: string | undefined) => {
  const cls =
    (risk && RISK_CLASSES[risk]) ||
    "bg-gray-700/40 text-gray-400 border-gray-600/30";
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-full border",
        cls,
      )}
    >
      {score == null ? "N/A" : `${score}/100`}
    </span>
  );
};

export default function QuickTools() {
  const { toast } = useToast();

  // ---- Tool 1: Cautare rapida firme ----
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FtsResult[]>([]);
  const [searching, setSearching] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    const q = debouncedQuery.trim();
    if (q === "") {
      setResults([]);
      setSearching(false);
      return;
    }
    let active = true;
    setSearching(true);
    api
      .searchFts(q, 20)
      .then((data) => {
        if (active) setResults(data);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setResults([]);
        const msg = err instanceof Error ? err.message : "Eroare la cautare";
        toast(msg, "error");
      })
      .finally(() => {
        if (active) setSearching(false);
      });
    // Guard impotriva raspunsurilor invechite (race condition)
    return () => {
      active = false;
    };
  }, [debouncedQuery, toast]);

  // ---- Tool 2: Scoring rapid (fara AI) ----
  const [cuisText, setCuisText] = useState("");
  const [scoreResults, setScoreResults] = useState<QuickScoreRow[]>([]);
  const [note, setNote] = useState("");
  const [scoring, setScoring] = useState(false);

  // Parsare CUI-uri: split pe linii/virgule, trim, elimina goale, plafon 20
  const parsedCuis = useMemo(
    () =>
      cuisText
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, MAX_CUIS),
    [cuisText],
  );

  const handleQuickScore = async () => {
    if (parsedCuis.length === 0) {
      toast("Introdu cel putin un CUI", "warning");
      return;
    }
    setScoring(true);
    try {
      const data = await api.quickScore(parsedCuis);
      setScoreResults(data.results);
      setNote(data.note);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Eroare la calcularea scorurilor";
      toast(msg, "error");
    } finally {
      setScoring(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Instrumente Rapide</h1>
        <p className="text-sm text-gray-500 mt-1">
          Cautare instant in baza de date si scoring rapid fara analiza AI
        </p>
      </div>

      {/* Tool 1: Cautare rapida firme */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5 text-accent-primary" />
          <h2 className="text-lg font-semibold text-white">
            Cautare rapida firme
          </h2>
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            className="input-field w-full pl-9 pr-9"
            placeholder="Cauta dupa nume sau CUI..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Cauta firme"
          />
          {searching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 animate-spin" />
          )}
        </div>

        {results.length > 0 && (
          <ul className="rounded-lg border border-dark-border divide-y divide-dark-border overflow-hidden">
            {results.map((r) => (
              <li key={r.id}>
                <Link
                  to={`/company/${r.id}`}
                  className="flex items-center gap-3 p-3 hover:bg-dark-hover transition-colors group"
                >
                  <Building2 className="w-5 h-5 text-accent-secondary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate group-hover:text-accent-secondary">
                      {r.name}
                    </p>
                    <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-0.5 text-xs text-gray-500">
                      <span>CUI: {r.cui}</span>
                      {r.caen_code && <span>CAEN: {r.caen_code}</span>}
                      {r.county && <span>{r.county}</span>}
                      {r.city && <span>{r.city}</span>}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-accent-secondary shrink-0" />
                </Link>
              </li>
            ))}
          </ul>
        )}

        {debouncedQuery.trim() !== "" && !searching && results.length === 0 && (
          <p className="text-sm text-gray-500">Niciun rezultat</p>
        )}
      </div>

      {/* Tool 2: Scoring rapid (fara AI) */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-accent-primary" />
          <h2 className="text-lg font-semibold text-white">
            Scoring rapid (fara AI)
          </h2>
        </div>

        <p className="text-sm text-gray-500">
          Lipeste pana la {MAX_CUIS} de CUI-uri (cate unul pe linie sau separate
          prin virgula).
        </p>

        <textarea
          className="input-field w-full h-32 font-mono text-sm resize-y"
          placeholder={"123456\n789012\n5555555, 6666666"}
          value={cuisText}
          onChange={(e) => setCuisText(e.target.value)}
          aria-label="Lista CUI-uri pentru scoring rapid"
        />

        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={handleQuickScore}
            disabled={scoring || parsedCuis.length === 0}
            className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {scoring ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Calculator className="w-4 h-4" />
            )}
            Calculeaza scoruri
          </button>
          <span className="text-xs text-gray-500">
            {parsedCuis.length} / {MAX_CUIS} CUI-uri detectate
          </span>
        </div>

        {scoreResults.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-dark-border">
                  <th className="py-2 pr-4 font-medium">CUI</th>
                  <th className="py-2 pr-4 font-medium">Nume</th>
                  <th className="py-2 pr-4 font-medium">CA (RON)</th>
                  <th className="py-2 pr-4 font-medium">Angajati</th>
                  <th className="py-2 pr-4 font-medium">Scor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border">
                {scoreResults.map((row, i) => (
                  <tr key={`${row.cui}-${i}`} className="text-gray-300">
                    <td className="py-2 pr-4 font-mono whitespace-nowrap">
                      {row.cui}
                    </td>
                    <td className="py-2 pr-4">
                      {row.error ? (
                        <span className="text-red-400 text-xs">
                          {row.error}
                        </span>
                      ) : (
                        (row.name ?? "-")
                      )}
                    </td>
                    <td className="py-2 pr-4 font-mono whitespace-nowrap">
                      {formatCA(row.ca_last_year)}
                    </td>
                    <td className="py-2 pr-4 font-mono">
                      {row.angajati ?? "-"}
                    </td>
                    <td className="py-2 pr-4">
                      {scoreBadge(row.quick_score, row.risk)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {note && <p className="text-xs text-gray-500 mt-1">{note}</p>}
      </div>
    </div>
  );
}
