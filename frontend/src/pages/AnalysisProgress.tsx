import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  Pause,
  Download,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { Job, WSMessage } from "@/lib/types";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";

export default function AnalysisProgress() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<{ text: string; type: string }[]>([]);
  const [reportId, setReportId] = useState<string | null>(null);

  // Load job on mount
  useEffect(() => {
    if (!id) return;
    api.getJob(id).then(setJob).catch(() => toast("Eroare la incarcarea jobului", "error"));
  }, [id]);

  // WebSocket for real-time progress
  const onMessage = (msg: WSMessage) => {
    if (msg.type === "progress") {
      setJob((prev) =>
        prev
          ? {
              ...prev,
              progress_percent: msg.percent ?? prev.progress_percent,
              current_step: msg.step ?? prev.current_step,
              status: (msg.status as Job["status"]) ?? prev.status,
            }
          : prev
      );
    }
    if (msg.type === "agent_complete") {
      setLogs((prev) => [
        ...prev,
        {
          text: `Agent ${msg.agent} finalizat (${msg.status})`,
          type: "success",
        },
      ]);
    }
    if (msg.type === "agent_warning") {
      setLogs((prev) => [
        ...prev,
        { text: msg.message || "Warning", type: "warning" },
      ]);
    }
    if (msg.type === "job_complete") {
      setJob((prev) =>
        prev ? { ...prev, status: "DONE", progress_percent: 100 } : prev
      );
      if (msg.report_id) setReportId(msg.report_id);
      setLogs((prev) => [
        ...prev,
        { text: `Analiza finalizata! Formate: ${(msg.formats || []).join(", ").toUpperCase() || "N/A"}`, type: "success" },
      ]);
    }
    if (msg.type === "job_failed") {
      setJob((prev) =>
        prev
          ? { ...prev, status: "FAILED", error_message: msg.error || null }
          : prev
      );
      setLogs((prev) => [
        ...prev,
        { text: msg.error || "Eroare fatala", type: "error" },
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
          <span className="text-sm font-mono text-white">
            {job.progress_percent}%
          </span>
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
          <div className="space-y-2 max-h-60 overflow-y-auto">
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
                <span className="text-gray-400">{log.text}</span>
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
