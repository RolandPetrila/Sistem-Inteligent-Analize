import { useState, useEffect, useRef, useCallback } from "react";
import { Upload, Download, Loader2, CheckCircle, XCircle, FileSearch } from "lucide-react";
import clsx from "clsx";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { logAction } from "@/lib/logger";
import { validateCUI } from "@/lib/cui-validator";

interface BatchStatus {
  batch_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  total: number;
  completed: number;
  failed: number;
  current_cui: string;
}

interface CsvPreviewRow {
  raw: string;
  cui: string;
  valid: boolean;
  error?: string;
}

interface ServerPreview {
  valid_count: number;
  invalid_count: number;
  valid_cuis: string[];
  invalid_entries: { line: number; cui: string; error: string }[];
  estimated_time_minutes: number;
}

export default function BatchAnalysis() {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [csvPreview, setCsvPreview] = useState<CsvPreviewRow[] | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [serverPreview, setServerPreview] = useState<ServerPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewConfirmed, setPreviewConfirmed] = useState(false);

  // R2 fix: CSV header keywords to detect and skip header row
  const CSV_HEADER_KEYWORDS = ["cui", "firma", "company", "denumire", "nume", "name", "cod"];

  // Parse CSV file client-side for preview and validation
  const parseCSVFile = useCallback(async (f: File) => {
    const text = await f.text();
    let lines = text.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);

    // R2 fix: Skip header row if first row contains known header keywords
    if (lines.length > 0) {
      const firstRow = lines[0].toLowerCase().replace(/"/g, "").trim();
      const isHeader = CSV_HEADER_KEYWORDS.some((kw) => firstRow.includes(kw));
      if (isHeader) {
        lines = lines.slice(1);
      }
    }

    const rows: CsvPreviewRow[] = lines.map((line) => {
      // Extract first column (handles comma/semicolon separators and quotes)
      const raw = line.split(/[,;]/)[0].replace(/"/g, "").trim();
      // Strip RO prefix for validation
      const cuiClean = raw.toUpperCase().replace(/^RO/, "").replace(/\s/g, "");
      if (!cuiClean) return { raw, cui: cuiClean, valid: false, error: "Linie goala" };
      const result = validateCUI(cuiClean);
      return { raw, cui: result.cui, valid: result.valid, error: result.error };
    });
    setCsvPreview(rows);
    setShowPreview(true);
  }, []);

  // C23 fix: Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setSubmitting(true);
    logAction("BatchAnalysis", "upload", { fileName: file.name, size: file.size });

    try {
      const data = await api.uploadBatch(file);
      toast(`Batch pornit: ${data.total_cuis} firme`, "success");

      // Start polling (C23 fix: use ref for cleanup on unmount)
      setPolling(true);
      if (intervalRef.current) clearInterval(intervalRef.current);
      const interval = setInterval(async () => {
        try {
          const status = await api.getBatchStatus(data.batch_id) as unknown as BatchStatus;
          setBatch(status);

          if (status.status === "DONE" || status.status === "FAILED") {
            clearInterval(interval);
            intervalRef.current = null;
            setPolling(false);
            if (status.status === "DONE") {
              toast("Batch complet! Descarca ZIP-ul.", "success");
            }
          }
        } catch {
          clearInterval(interval);
          intervalRef.current = null;
          setPolling(false);
          toast("Eroare la verificarea statusului batch-ului", "warning");
        }
      }, 3000);
      intervalRef.current = interval;

      setBatch({
        batch_id: data.batch_id,
        status: "RUNNING",
        progress_percent: 0,
        current_step: "Pornire...",
        total: data.total_cuis,
        completed: 0,
        failed: 0,
        current_cui: "",
      });
    } catch {
      toast("Eroare la pornirea batch-ului", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Analiza Batch</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload CSV cu CUI-uri pentru analiza in serie
        </p>
      </div>

      {/* Upload Area */}
      {!batch && (
        <div className="card max-w-xl space-y-4">
          <div
            className={clsx(
              "border-2 border-dashed rounded-xl p-8 text-center transition-colors",
              file ? "border-accent-primary/50 bg-accent-primary/5" : "border-dark-border"
            )}
          >
            <Upload className="w-10 h-10 text-gray-500 mx-auto mb-3" />
            <p className="text-sm text-gray-400 mb-3">
              {file ? file.name : "Selecteaza un fisier CSV cu CUI-uri (un CUI per linie)"}
            </p>
            <input
              type="file"
              accept=".csv"
              className="hidden"
              id="csv-upload"
              onChange={async (e) => {
                const f = e.target.files?.[0] || null;
                setFile(f);
                setCsvPreview(null);
                setShowPreview(false);
                setServerPreview(null);
                setPreviewConfirmed(false);
                if (f) {
                  parseCSVFile(f);
                  // Apeleaza preview server-side
                  setPreviewLoading(true);
                  try {
                    const prev = await api.previewBatch(f);
                    setServerPreview(prev);
                  } catch {
                    // Preview server-side optional — continua cu preview client
                  } finally {
                    setPreviewLoading(false);
                  }
                }
              }}
            />
            <label
              htmlFor="csv-upload"
              className="btn-secondary cursor-pointer inline-block"
            >
              {file ? "Schimba fisier" : "Alege CSV"}
            </label>
          </div>

          <p className="text-xs text-gray-600">
            Format: un CUI per linie, maxim 50 CUI-uri. Exemplu: 43978110
          </p>

          {/* CSV Preview */}
          {showPreview && csvPreview && csvPreview.length > 0 && (
            <div className="border border-dark-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 bg-dark-surface">
                <div className="flex items-center gap-2">
                  <FileSearch className="w-4 h-4 text-accent-secondary" />
                  <span className="text-sm font-medium text-gray-300">
                    Previzualizare CSV
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-400">{csvPreview.length} randuri</span>
                  <span className="text-green-400">
                    {csvPreview.filter((r) => r.valid).length} valide
                  </span>
                  {csvPreview.filter((r) => !r.valid).length > 0 && (
                    <span className="text-red-400">
                      {csvPreview.filter((r) => !r.valid).length} invalide
                    </span>
                  )}
                </div>
              </div>
              <div className="max-h-48 overflow-y-auto">
                {csvPreview.map((row, i) => (
                  <div
                    key={i}
                    className={clsx(
                      "flex items-center justify-between px-3 py-1.5 text-sm border-t border-dark-border/50",
                      i % 2 === 0 ? "bg-dark-card" : "bg-dark-surface"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {row.valid ? (
                        <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      )}
                      <span className={row.valid ? "text-gray-300" : "text-red-300"}>
                        {row.raw || "(gol)"}
                      </span>
                    </div>
                    {!row.valid && row.error && (
                      <span className="text-[10px] text-red-400 ml-2">{row.error}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Server Preview Summary */}
          {previewLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Validare server...
            </div>
          )}
          {serverPreview && !previewLoading && (
            <div className="border border-dark-border rounded-lg p-3 bg-dark-surface space-y-2">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-green-400 font-medium">{serverPreview.valid_count} CUI-uri valide</span>
                {serverPreview.invalid_count > 0 && (
                  <span className="text-red-400">{serverPreview.invalid_count} invalide</span>
                )}
                <span className="text-gray-500">~{serverPreview.estimated_time_minutes} min estimat</span>
              </div>
              {serverPreview.invalid_entries.length > 0 && (
                <div className="space-y-0.5">
                  {serverPreview.invalid_entries.map((e, i) => (
                    <p key={i} className="text-[11px] text-red-400">
                      Linia {e.line}: {e.cui} — {e.error}
                    </p>
                  ))}
                </div>
              )}
              {!previewConfirmed && serverPreview.valid_count > 0 && (
                <button
                  type="button"
                  onClick={() => setPreviewConfirmed(true)}
                  className="btn-primary text-sm w-full mt-1"
                >
                  Confirma si pregateste analiza
                </button>
              )}
              {previewConfirmed && (
                <p className="text-xs text-green-400 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Confirmat — apasa Porneste pentru a incepe
                </p>
              )}
            </div>
          )}

          {file && (
            <button
              onClick={handleUpload}
              disabled={
                submitting ||
                (csvPreview !== null && csvPreview.filter((r) => r.valid).length === 0) ||
                (serverPreview !== null && !previewConfirmed)
              }
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Se proceseaza...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  {csvPreview
                    ? `Porneste Analiza (${csvPreview.filter((r) => r.valid).length} CUI-uri)`
                    : "Porneste Batch Analysis"}
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Batch Progress */}
      {batch && (
        <div className="card max-w-xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Progres Batch</h2>
            <span
              className={clsx(
                "text-xs font-medium px-2 py-1 rounded",
                batch.status === "DONE"
                  ? "bg-green-500/20 text-green-400"
                  : batch.status === "FAILED"
                  ? "bg-red-500/20 text-red-400"
                  : "bg-blue-500/20 text-blue-400"
              )}
            >
              {batch.status}
            </span>
          </div>

          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{batch.current_step}</span>
              <span>{batch.progress_percent}%</span>
            </div>
            <div className="w-full h-2 bg-dark-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-accent-primary rounded-full transition-all duration-500"
                style={{ width: `${batch.progress_percent}%` }}
              />
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-3 bg-dark-surface rounded-lg">
              <p className="text-2xl font-bold text-white">{batch.total}</p>
              <p className="text-xs text-gray-500">Total</p>
            </div>
            <div className="text-center p-3 bg-dark-surface rounded-lg">
              <div className="flex items-center justify-center gap-1">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <p className="text-2xl font-bold text-green-400">{batch.completed}</p>
              </div>
              <p className="text-xs text-gray-500">Complete</p>
            </div>
            <div className="text-center p-3 bg-dark-surface rounded-lg">
              <div className="flex items-center justify-center gap-1">
                <XCircle className="w-4 h-4 text-red-400" />
                <p className="text-2xl font-bold text-red-400">{batch.failed}</p>
              </div>
              <p className="text-xs text-gray-500">Erori</p>
            </div>
          </div>

          {batch.current_cui && polling && (
            <p className="text-xs text-gray-500 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              Analizeaza CUI: {batch.current_cui}
            </p>
          )}

          {/* Download ZIP */}
          {batch.status === "DONE" && (
            <a
              href={`/api/batch/${batch.batch_id}/download`}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Descarca ZIP ({batch.completed} rapoarte)
            </a>
          )}

          {/* New batch */}
          {(batch.status === "DONE" || batch.status === "FAILED") && (
            <button
              onClick={() => {
                setBatch(null);
                setFile(null);
              }}
              className="btn-secondary w-full"
            >
              Batch Nou
            </button>
          )}
        </div>
      )}
    </div>
  );
}
