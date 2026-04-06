import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  Pause,
  Download,
  RefreshCw,
  Timer,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { Job, WSMessage } from "@/lib/types";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import { sendBrowserNotification } from "@/lib/notifications";

export default function AnalysisProgress() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<{ text: string; type: string; ts: string }[]>([]);
  const [reportId, setReportId] = useState<string | null>(null);
  const runStartRef = useRef<number | null>(null);

  // Load job on mount
  useEffect(() => {
    if (!id) return;
    logAction("AnalysisProgress", "open", { jobId: id });
    api.getJob(id).then(setJob).catch(() => toast("Eroare la incarcarea jobului", "error"));
  }, [id]);

  // Track when the job started RUNNING for ETA calculation
  useEffect(() => {
    if (job?.status === "RUNNING" && runStartRef.current === null) {
      runStartRef.current = Date.now();
    }
    if (job?.status !== "RUNNING") {
      runStartRef.current = null;
    }
  }, [job?.status]);

  // Calculate ETA in seconds based on elapsed time and progress
  const computeETA = (): number | null => {
    if (!job || job.status !== "RUNNING" || !runStartRef.current) return null;
    const progress = job.progress_percent;
    if (progress <= 5) return null; // too early to estimate
    const elapsed = (Date.now() - runStartRef.current) / 1000;
    const totalEstimated = (elapsed / progress) * 100;
    const remaining = Math.max(0, Math.round(totalEstimated - elapsed));
    return remaining;
  };

  const etaSeconds = computeETA();

  // WebSocket for real-time progress
  const onMessage = (msg: WSMessage) => {
    if (msg.type === "progress") {
      setJob((prev) =>
        prev
          ? {
              ...prev,
              // R2 fix: Guard progress from going backwards — use Math.max
              progress_percent: Math.max(
                msg.percent ?? prev.progress_percent,
                prev.progress_percent
              ),
              current_step: msg.step ?? prev.current_step,
              status: (msg.status as Job["status"]) ?? prev.status,
            }
          : prev
      );
    }
    // F2-8: Helper pentru timestamp curent
    const nowTs = () => new Date().toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    if (msg.type === "progress" && msg.step) {
      setLogs((prev) => {
        // Evita duplicate consecutive de steps identice
        if (prev.length > 0 && prev[prev.length - 1].text === msg.step) return prev;
        return [...prev, { text: msg.step!, type: "info", ts: nowTs() }];
      });
    }
    if (msg.type === "agent_complete") {
      setLogs((prev) => [
        ...prev,
        {
          text: `Agent ${msg.agent} finalizat (${msg.status})`,
          type: "success",
          ts: nowTs(),
        },
      ]);
    }
    if (msg.type === "agent_warning") {
      setLogs((prev) => [
        ...prev,
        { text: msg.message || "Warning", type: "warning", ts: nowTs() },
      ]);
    }
    if (msg.type === "job_complete") {
      setJob((prev) =>
        prev ? { ...prev, status: "DONE", progress_percent: 100 } : prev
      );
      if (msg.report_id) setReportId(msg.report_id);
      logAction("AnalysisProgress", "complete", { jobId: id, reportId: msg.report_id, formats: msg.formats });
      setLogs((prev) => [
        ...prev,
        { text: `Analiza finalizata! Formate: ${(msg.formats || []).join(", ").toUpperCase() || "N/A"}`, type: "success", ts: nowTs() },
      ]);
      // F3-9: Browser notification la finalizare analiza
      sendBrowserNotification(
        "Analiza finalizata",
        "Raport disponibil — deschide pentru a vedea scorul",
        msg.report_id ? `/report/${msg.report_id}` : undefined
      );
    }
    if (msg.type === "job_failed") {
      setJob((prev) =>
        prev
          ? { ...prev, status: "FAILED", error_message: msg.error || null }
          : prev
      );
      logAction("AnalysisProgress", "failed", { jobId: id, error: msg.error });
      setLogs((prev) => [
        ...prev,
        { text: msg.error || "Eroare fatala", type: "error", ts: nowTs() },
      ]);
    }
  };

  useWebSocket(id || "", onMessage, !!id && job?.status === "RUNNING");

  if (!job) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
      </div>
    );
  }

  const statusIcon = {
    PENDING: <Loader2 className="w-6 h-6 text-gray-400" />,
    RUNNING: (
      <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />
    ),
    PAUSED: <Pause className="w-6 h-6 text-yellow-400" />,
    DONE: <CheckCircle className="w-6 h-6 text-green-400" />,
    FAILED: <XCircle className="w-6 h-6 text-red-400" />,
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        {statusIcon[job.status]}
        <div>
          <h1 className="text-xl font-bold text-white">
            {ANALYSIS_TYPE_LABELS[job.type] || job.type}
          </h1>
          <p className="text-sm text-gray-500">Job: {job.id.slice(0, 8)}...</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">Progres</span>
          <div className="flex items-center gap-3">
            {etaSeconds !== null && etaSeconds > 0 && (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Timer className="w-3 h-3" />
                ~{etaSeconds >= 60 ? `${Math.floor(etaSeconds / 60)}m ${etaSeconds % 60}s` : `${etaSeconds}s`} ramase
              </span>
            )}
            <span className="text-sm font-mono text-white">
              {job.progress_percent}%
            </span>
          </div>
        </div>
        <div className="w-full h-3 bg-dark-border rounded-full overflow-hidden">
          <div
            className={clsx(
              "h-full rounded-full transition-all duration-500",
              job.status === "FAILED" ? "bg-red-500" : "bg-accent-primary"
            )}
            style={{ width: `${job.progress_percent}%` }}
          />
        </div>
        {job.current_step && (
          <p className="text-xs text-gray-500 mt-2">{job.current_step}</p>
        )}
      </div>

      {/* Error + 10C M12.3: Retry Button */}
      {job.error_message && (
        <div className="card border-red-500/30 bg-red-500/5">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-300">{job.error_message}</p>
              {job.status === "FAILED" && id && (
                <button
                  onClick={() => {
                    api.startJob(id).then(() => {
                      toast("Job repornit", "success");
                      setJob(prev => prev ? { ...prev, status: "RUNNING", progress_percent: 0, error_message: null } : prev);
                    }).catch(() => toast("Nu s-a putut reporni jobul", "error"));
                  }}
                  className="mt-2 text-xs px-3 py-1.5 rounded bg-accent-primary/20 text-accent-light
                             hover:bg-accent-primary/30 transition-colors"
                >
                  Reincearca analiza
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* B26: Retry individual sources when job is DONE or FAILED */}
      {(job.status === "DONE" || job.status === "FAILED") && id && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Reincercare Surse Individuale
          </h2>
          <p className="text-xs text-gray-600 mb-3">
            Reinterogheaza o sursa specifica fara a relua toata analiza
          </p>
          <div className="flex flex-wrap gap-2">
            {["anaf", "openapi", "bilant", "bnr", "seap"].map((source) => (
              <button
                key={source}
                onClick={() => {
                  api.retrySource(id, source)
                    .then((res) => {
                      if (res.success) {
                        toast(`Sursa ${source.toUpperCase()} reinterogata cu succes`, "success");
                        setLogs((prev) => [...prev, { text: `Retry ${source}: OK`, type: "success", ts: new Date().toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) }]);
                      } else {
                        toast(`Eroare ${source}: ${res.error || "necunoscuta"}`, "warning");
                        setLogs((prev) => [...prev, { text: `Retry ${source}: ${res.error || "eroare"}`, type: "warning", ts: new Date().toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) }]);
                      }
                    })
                    .catch(() => toast(`Eroare la reinterogarea sursei ${source}`, "error"));
                }}
                className="text-xs px-3 py-1.5 rounded bg-dark-surface border border-dark-border
                           hover:border-accent-primary hover:text-accent-light transition-colors
                           flex items-center gap-1.5 text-gray-400"
              >
                <RefreshCw className="w-3 h-3" />
                {source.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Done */}
      {job.status === "DONE" && (
        <div className="card border-green-500/30 bg-green-500/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <p className="text-sm text-green-300">
                Analiza finalizata cu succes!
              </p>
            </div>
            <Link
              to={reportId ? `/report/${reportId}` : "/reports"}
              className="btn-primary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Vezi Raport
            </Link>
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Jurnal Activitate
        </h2>
        {logs.length === 0 ? (
          <p className="text-xs text-gray-600">
            Nicio activitate inca...
          </p>
        ) : (
          <div className="space-y-1.5 max-h-60 overflow-y-auto font-mono">
            {logs.map((log, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-xs"
              >
                {log.type === "success" && (
                  <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" />
                )}
                {log.type === "warning" && (
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0 mt-0.5" />
                )}
                {log.type === "error" && (
                  <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                )}
                {log.type === "info" && (
                  <span className="w-3.5 h-3.5 shrink-0 mt-0.5 text-blue-400 font-bold text-[10px] flex items-center justify-center">▸</span>
                )}
                <span className={clsx(
                  "flex-1",
                  log.type === "success" ? "text-green-300" :
                  log.type === "warning" ? "text-yellow-300" :
                  log.type === "error" ? "text-red-300" :
                  "text-gray-400"
                )}>{log.text}</span>
                {log.ts && (
                  <span className="text-[10px] text-gray-600 shrink-0">{log.ts}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        {job.status === "PENDING" && (
          <button
            className="btn-primary"
            onClick={() => api.startJob(job.id).then(() => setJob({ ...job, status: "RUNNING" }))}
          >
            Porneste Analiza
          </button>
        )}
        {(job.status === "RUNNING" || job.status === "PENDING") && (
          <button
            className="btn-secondary"
            onClick={() =>
              api.cancelJob(job.id).then(() => setJob({ ...job, status: "FAILED" }))
            }
          >
            Anuleaza
          </button>
        )}
        <Link to="/" className="btn-secondary">
          Inapoi la Dashboard
        </Link>
      </div>
    </div>
  );
}
