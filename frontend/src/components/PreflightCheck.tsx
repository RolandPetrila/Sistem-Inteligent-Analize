import { useState } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import { api, type PreflightResult, type PreflightItem } from "@/lib/api";
import { useToast } from "@/components/Toast";

function Row({ item }: { item: PreflightItem }) {
  return (
    <div className="flex items-start gap-2 py-0.5">
      {item.ok ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-green-400 mt-0.5 shrink-0" />
      ) : (
        <XCircle className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
      )}
      <div className="min-w-0">
        <span className="text-xs font-medium text-gray-200">
          {item.service}
        </span>
        <span className="text-[11px] text-gray-500 ml-2">{item.message}</span>
      </div>
    </div>
  );
}

/**
 * Verificare LIVE a tuturor conexiunilor (surse + provideri AI) inainte de o
 * analiza. Un singur apel -> GET /api/settings/preflight ruleaza ~18 teste reale
 * concurent server-side si intoarce verdict GATA/NU-E-GATA. Centralizeaza in
 * aplicatie ce facea starterul de pe desktop (tools/preflight_check.py).
 */
export default function PreflightCheck() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PreflightResult | null>(null);
  const [open, setOpen] = useState(false);

  const run = async () => {
    setLoading(true);
    setOpen(true);
    try {
      const r = await api.preflight();
      setResult(r);
      toast(
        r.ready ? "Conexiuni OK — gata de executie" : `Conexiuni: ${r.verdict}`,
        r.ready ? "success" : "warning",
      );
    } catch {
      setResult(null);
      toast("Verificarea conexiunilor a esuat", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-medium text-gray-200">
            Verifica conexiunile inainte de a porni
          </span>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="btn-secondary text-xs flex items-center gap-1.5 whitespace-nowrap"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          {loading ? "Verific..." : result ? "Reverifica" : "Verifica"}
        </button>
      </div>

      {open && (
        <div className="mt-3">
          {loading && !result && (
            <p className="text-xs text-gray-500">
              Testez live fiecare sursa si provider AI... (~10-15s)
            </p>
          )}

          {result && (
            <>
              <div
                className={clsx(
                  "rounded-lg px-3 py-2 mb-3 text-sm font-semibold flex items-center gap-2",
                  result.ready
                    ? "bg-green-900/25 text-green-300"
                    : "bg-red-900/25 text-red-300",
                )}
              >
                {result.ready ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : (
                  <XCircle className="w-4 h-4" />
                )}
                {result.ready ? "GATA DE EXECUTIE" : "NU E GATA"}
                <span className="ml-auto text-xs font-normal text-gray-400">
                  {result.summary.ok}/{result.summary.total} conectate
                </span>
              </div>

              {!result.ready && result.critical_down.length > 0 && (
                <p className="text-xs text-red-300 mb-2">
                  Surse critice picate: {result.critical_down.join(", ")}
                </p>
              )}
              {!result.ready && !result.synthesis_ok && (
                <p className="text-xs text-red-300 mb-2">
                  Sinteza indisponibila: nici Claude, nici un provider AI de
                  rezerva.
                </p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">
                    Sinteza (Claude Opus)
                  </p>
                  <Row
                    item={{
                      service: "claude",
                      ok: result.claude.ok,
                      message: result.claude.message,
                    }}
                  />
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 mt-2 mb-1">
                    Provideri AI (rezerva)
                  </p>
                  {result.categories.ai.map((i) => (
                    <Row key={i.service} item={i} />
                  ))}
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">
                    Surse principale (oficiale)
                  </p>
                  {result.categories.principale.map((i) => (
                    <Row key={i.service} item={i} />
                  ))}
                </div>
              </div>

              <details className="mt-3">
                <summary className="text-xs text-gray-400 cursor-pointer select-none">
                  Surse secundare + cele mereu indisponibile
                </summary>
                <div className="mt-2">
                  {result.categories.secundare.map((i) => (
                    <Row key={i.service} item={i} />
                  ))}
                  <p className="text-[11px] text-gray-500 mt-2">
                    Mereu indisponibile (normal, moarte la furnizor, NU te
                    impiedica): {result.known_dead.join(", ")}
                  </p>
                </div>
              </details>
            </>
          )}
        </div>
      )}
    </div>
  );
}
