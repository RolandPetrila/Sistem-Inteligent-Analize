import { useState, useEffect, useRef } from "react";
import { Upload, Download, Loader2, CheckCircle, XCircle } from "lucide-react";
import clsx from "clsx";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { logAction } from "@/lib/logger";

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

export default function BatchAnalysis() {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
              onChange={(e) => setFile(e.target.files?.[0] || null)}
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

          {file && (
            <button
              onClick={handleUpload}
              disabled={submitting}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Se proceseaza...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" /> Porneste Batch Analysis
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
