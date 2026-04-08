import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ReportDelta } from "@/lib/types";

export function DeltaView({ reportId }: { reportId: string }) {
  const [delta, setDelta] = useState<ReportDelta | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getReportDelta(reportId)
      .then(setDelta)
      .catch(() => setDelta(null))
      .finally(() => setLoading(false));
  }, [reportId]);

  if (loading)
    return (
      <div className="card animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-1/3 mb-3" />
        <div className="h-6 bg-gray-700 rounded w-1/2" />
      </div>
    );

  if (!delta?.has_delta)
    return (
      <div className="card text-center py-8">
        <p className="text-gray-500">
          Prima analiza — fara date anterioare pentru comparatie
        </p>
      </div>
    );

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-4">
        <h3 className="text-lg font-semibold">Evolutie Scor</h3>
        <div className="flex items-center gap-2 text-2xl font-bold">
          <span className="text-gray-400">{delta.previous_score}</span>
          <span className="text-gray-500">→</span>
          <span>{delta.current_score}</span>
          {delta.score_delta !== undefined && (
            <span
              className={`text-lg ml-2 ${delta.score_delta > 0 ? "text-green-400" : delta.score_delta < 0 ? "text-red-400" : "text-gray-400"}`}
            >
              ({delta.score_delta > 0 ? "+" : ""}
              {delta.score_delta})
            </span>
          )}
        </div>
      </div>

      {delta.changes && delta.changes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
            Modificari detectate
          </h4>
          {delta.changes.map((change, i) => (
            <div
              key={i}
              className="flex justify-between items-center py-2 border-b border-gray-800"
            >
              <span className="text-gray-300">{change.field}</span>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-red-400 line-through">
                  {String(change.old ?? "—")}
                </span>
                <span className="text-gray-500">→</span>
                <span className="text-green-400 font-medium">
                  {String(change.new ?? "—")}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
