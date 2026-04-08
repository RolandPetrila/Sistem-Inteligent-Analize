import {
  FileText,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import type { TimelineEvent } from "@/lib/types";

interface CompanyTimelineProps {
  timeline: TimelineEvent[];
  loading: boolean;
}

export function CompanyTimeline({ timeline, loading }: CompanyTimelineProps) {
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-400 uppercase mb-4">
        Timeline
      </h3>

      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />
        </div>
      ) : timeline.length === 0 ? (
        <p className="text-gray-600 text-sm py-4 text-center">
          Nicio activitate inregistrata
        </p>
      ) : (
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-dark-border" />
          <div className="space-y-4">
            {timeline.map((event, i) => {
              const TimelineIcon =
                event.type === "report"
                  ? FileText
                  : event.type === "score_change"
                    ? event.detail?.includes("-") ||
                      event.detail?.includes("scadere")
                      ? TrendingDown
                      : TrendingUp
                    : AlertTriangle;
              const iconColor =
                event.type === "report"
                  ? "text-blue-400 bg-blue-500/10"
                  : event.type === "score_change"
                    ? event.detail?.includes("-") ||
                      event.detail?.includes("scadere")
                      ? "text-red-400 bg-red-500/10"
                      : "text-green-400 bg-green-500/10"
                    : "text-yellow-400 bg-yellow-500/10";

              return (
                <div key={i} className="flex items-start gap-4 pl-1">
                  <div
                    className={clsx(
                      "w-7 h-7 rounded-full flex items-center justify-center shrink-0 z-10",
                      iconColor,
                    )}
                  >
                    <TimelineIcon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0 pb-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm text-gray-300 font-medium">
                        {event.title}
                      </p>
                      <span className="text-[10px] text-gray-600 shrink-0">
                        {new Date(event.date).toLocaleDateString("ro-RO", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                    {event.detail && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {event.detail}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
