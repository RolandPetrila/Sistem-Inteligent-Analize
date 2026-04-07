import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileText,
  Building2,
  CheckCircle,
  Clock,
  TrendingUp,
  PlusCircle,
  Zap,
  AlertCircle,
  Activity,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Shield,
} from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import type { Stats, Job, RiskMover } from "@/lib/types";
import { JOB_STATUS_LABELS, ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import clsx from "clsx";

interface IntegrationStatus {
  has_tavily: boolean;
  has_gemini: boolean;
  has_groq: boolean;
  has_cerebras: boolean;
  has_telegram: boolean;
  has_email: boolean;
  synthesis_mode: string;
}

const SkeletonCard = () => (
  <div className="card animate-pulse">
    <div className="h-4 bg-gray-700 rounded w-1/3 mb-3" />
    <div className="h-8 bg-gray-700 rounded w-2/3 mb-2" />
    <div className="h-3 bg-gray-700 rounded w-1/2" />
  </div>
);

const SkeletonDashboard = () => (
  <div className="space-y-6">
    <div className="h-8 bg-dark-card rounded w-48 animate-pulse" />
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 card animate-pulse h-64" />
      <div className="card animate-pulse h-64" />
    </div>
  </div>
);

export default function Dashboard() {
  const { toast } = useToast();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(
    null,
  );
  const [healthData, setHealthData] = useState<Record<string, unknown> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getStats(),
      api.listJobs({ limit: 5 }),
      api.getSettings().catch(() => null),
      api.healthDeep().catch(() => null),
    ])
      .then(([s, j, settings, health]) => {
        setStats(s);
        setRecentJobs(j.jobs);
        if (settings) setIntegrations(settings);
        if (health) setHealthData(health);
        logAction("Dashboard", "loaded", {
          companies: s?.total_companies,
          reports: s?.total_reports,
          jobs: s?.total_jobs,
        });
      })
      .catch(() => toast("Eroare la incarcarea dashboard-ului", "error"))
      .finally(() => setLoading(false));

    // 10C M1.1: Refresh health status every 60s
    const healthInterval = setInterval(() => {
      api
        .healthDeep()
        .then(setHealthData)
        .catch(() => {});
    }, 60_000);
    return () => clearInterval(healthInterval);
  }, []);

  if (loading) return <SkeletonDashboard />;

  // Trend indicator: compare jobs_this_month with a previous reference
  // The API doesn't expose last month's count directly, so we show a visual placeholder
  // based on whether the current month value is above/below the monthly average
  const monthlyAvg =
    stats && stats.total_jobs > 0
      ? Math.round(stats.total_jobs / Math.max(1, 6)) // rough 6-month avg
      : null;
  const monthDelta =
    monthlyAvg !== null && stats
      ? (stats.jobs_this_month ?? 0) - monthlyAvg
      : null;

  const statCards = [
    {
      label: "Rapoarte Generate",
      value: stats?.total_reports ?? 0,
      icon: FileText,
      color: "text-accent-primary",
      trend: null as number | null,
    },
    {
      label: "Companii Analizate",
      value: stats?.total_companies ?? 0,
      icon: Building2,
      color: "text-blue-400",
      trend: null as number | null,
    },
    {
      label: "Joburi Finalizate",
      value: stats?.completed_jobs ?? 0,
      icon: CheckCircle,
      color: "text-green-400",
      trend: null as number | null,
    },
    {
      label: "Analize Luna Asta",
      value: stats?.jobs_this_month ?? 0,
      icon: TrendingUp,
      color: "text-purple-400",
      trend: monthDelta,
    },
  ];

  const integrationItems = integrations
    ? [
        { name: "ANAF", status: true, note: "API oficial v9" },
        { name: "ANAF Bilant", status: true, note: "Date financiare" },
        { name: "BNR", status: true, note: "Cursuri valutare" },
        { name: "Tavily", status: integrations.has_tavily, note: "Web search" },
        {
          name: "Groq AI",
          status: integrations.has_groq,
          note: "Sinteza rapida",
        },
        {
          name: "Gemini",
          status: integrations.has_gemini,
          note: "Fallback AI",
        },
        {
          name: "Claude CLI",
          status: integrations.synthesis_mode === "claude_code",
          note: "Sinteza premium",
        },
        {
          name: "Telegram",
          status: integrations.has_telegram,
          note: "Notificari",
        },
      ]
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Roland Intelligence System v1.1
          </p>
        </div>
        <Link
          to="/new-analysis"
          className="btn-primary flex items-center gap-2"
        >
          <PlusCircle className="w-4 h-4" />
          Analiza Noua
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">
                  {card.label}
                </p>
                <div className="flex items-end gap-2 mt-2">
                  <p className="text-3xl font-bold text-white">{card.value}</p>
                  {card.trend !== null && card.trend !== 0 && (
                    <span
                      className={clsx(
                        "flex items-center gap-0.5 text-xs font-medium mb-1",
                        card.trend > 0 ? "text-green-400" : "text-red-400",
                      )}
                    >
                      {card.trend > 0 ? (
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      ) : (
                        <ArrowDownRight className="w-3.5 h-3.5" />
                      )}
                      {card.trend > 0 ? "+" : ""}
                      {card.trend} vs medie
                    </span>
                  )}
                  {card.trend !== null && card.trend === 0 && (
                    <span className="flex items-center gap-0.5 text-xs font-medium mb-1 text-gray-500">
                      <Minus className="w-3.5 h-3.5" /> la medie
                    </span>
                  )}
                </div>
              </div>
              <card.icon className={clsx("w-8 h-8", card.color)} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Jobs - 2/3 width */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">
              Activitate Recenta
            </h2>
            <Link
              to="/reports"
              className="text-sm text-accent-secondary hover:text-accent-light"
            >
              Vezi toate
            </Link>
          </div>

          {recentJobs.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">Nicio analiza efectuata inca</p>
              <Link
                to="/new-analysis"
                className="text-accent-secondary hover:text-accent-light text-sm mt-2 inline-block"
              >
                Porneste prima analiza
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => {
                const statusConf = JOB_STATUS_LABELS[job.status] || {
                  label: job.status,
                  color: "text-gray-400",
                };
                return (
                  <Link
                    key={job.id}
                    to={
                      job.status === "RUNNING"
                        ? `/analysis/${job.id}`
                        : `/reports`
                    }
                    className="flex items-center justify-between p-3 rounded-lg
                               hover:bg-dark-hover transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-200">
                        {ANALYSIS_TYPE_LABELS[job.type] || job.type}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {new Date(job.created_at).toLocaleDateString("ro-RO", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* 10C M1.3: Completeness Gate Badge */}
                      {job.status === "DONE" &&
                        (job as unknown as Record<string, unknown>)
                          .completeness_score !== undefined &&
                        Number(
                          (job as unknown as Record<string, unknown>)
                            .completeness_score,
                        ) < 50 && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-900/50 text-red-400">
                            LOW DATA
                          </span>
                        )}
                      {job.status === "RUNNING" && (
                        <div className="w-24 h-1.5 bg-dark-border rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-primary rounded-full transition-all"
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                      )}
                      <span
                        className={clsx(
                          "text-xs font-medium",
                          statusConf.color,
                        )}
                      >
                        {statusConf.label}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Integration Status - 1/3 width */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Status Integrari
          </h2>
          <div className="space-y-2">
            {integrationItems.map((item) => {
              const content = (
                <div className="flex items-center justify-between py-1.5">
                  <div className="flex items-center gap-2">
                    {item.status ? (
                      <Zap className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-gray-600" />
                    )}
                    <span
                      className={clsx(
                        "text-sm",
                        item.status ? "text-gray-300" : "text-gray-600",
                      )}
                    >
                      {item.name}
                    </span>
                  </div>
                  <span
                    className={clsx(
                      "text-[10px] font-mono",
                      item.status ? "text-green-400" : "text-gray-600",
                    )}
                  >
                    {item.status ? "OK" : "---"}
                  </span>
                </div>
              );

              // Wrap unconfigured integrations as link to Settings
              return item.status ? (
                <div key={item.name}>{content}</div>
              ) : (
                <Link
                  key={item.name}
                  to="/settings"
                  className="block rounded hover:bg-dark-hover/50 transition-colors"
                  title={`Configureaza ${item.name} in Setari`}
                >
                  {content}
                </Link>
              );
            })}
          </div>
          <Link
            to="/settings"
            className="block text-center text-xs text-accent-secondary hover:text-accent-light mt-4 pt-3 border-t border-dark-border"
          >
            Configurare API Keys
          </Link>
        </div>
      </div>

      {/* N3: Risk Movers Widget — afiseaza toti moverii (F6-8: eliminat duplicatul hardcodat) */}
      <RiskMoversWidget />

      {/* 10C M1.1: Health Status Card (Live) */}
      {healthData && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-green-400" />
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
              Health Status (Live)
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(healthData)
              .filter(([k]) => k !== "status")
              .map(([key, val]) => {
                const isOk =
                  typeof val === "object" &&
                  val !== null &&
                  (val as Record<string, unknown>).status === "ok";
                const isFail =
                  typeof val === "object" &&
                  val !== null &&
                  (val as Record<string, unknown>).status !== "ok";
                return (
                  <div
                    key={key}
                    className={clsx(
                      "p-2 rounded-lg text-center",
                      isOk
                        ? "bg-green-900/20"
                        : isFail
                          ? "bg-red-900/20"
                          : "bg-dark-surface",
                    )}
                  >
                    <span
                      className={clsx(
                        "text-xs font-medium",
                        isOk
                          ? "text-green-400"
                          : isFail
                            ? "text-red-400"
                            : "text-gray-400",
                      )}
                    >
                      {isOk
                        ? "OK"
                        : isFail
                          ? "FAIL"
                          : typeof val === "string"
                            ? val
                            : "?"}
                    </span>
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      {key.replace(/_/g, " ")}
                    </p>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Trend Chart */}
      <TrendChart />

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Actiuni Rapide
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            to="/new-analysis"
            className="p-3 rounded-lg bg-dark-surface hover:bg-dark-hover transition-colors text-center"
          >
            <Building2 className="w-5 h-5 text-accent-primary mx-auto mb-1" />
            <span className="text-xs text-gray-400">Profil Firma</span>
          </Link>
          <Link
            to="/new-analysis"
            className="p-3 rounded-lg bg-dark-surface hover:bg-dark-hover transition-colors text-center"
          >
            <FileText className="w-5 h-5 text-blue-400 mx-auto mb-1" />
            <span className="text-xs text-gray-400">Evaluare Risc</span>
          </Link>
          <Link
            to="/companies"
            className="p-3 rounded-lg bg-dark-surface hover:bg-dark-hover transition-colors text-center"
          >
            <CheckCircle className="w-5 h-5 text-green-400 mx-auto mb-1" />
            <span className="text-xs text-gray-400">Companii</span>
          </Link>
          <Link
            to="/reports"
            className="p-3 rounded-lg bg-dark-surface hover:bg-dark-hover transition-colors text-center"
          >
            <TrendingUp className="w-5 h-5 text-purple-400 mx-auto mb-1" />
            <span className="text-xs text-gray-400">Rapoarte</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

function RiskMoversWidget() {
  const navigate = useNavigate();
  const [movers, setMovers] = useState<RiskMover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .getRiskMovers()
      .then((data) => setMovers((data.movers || []).slice(0, 5)))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-4 h-4 text-accent-secondary" />
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Risc in Schimbare
        </h2>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-dark-surface rounded-lg" />
          ))}
        </div>
      ) : error || movers.length === 0 ? (
        <div className="text-center py-6">
          <AlertTriangle className="w-6 h-6 text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Nicio schimbare detectata</p>
        </div>
      ) : (
        <div className="space-y-2">
          {movers.map((mover) => (
            <button
              key={mover.id}
              onClick={() => navigate(`/company/${mover.id}`)}
              className="w-full flex items-center justify-between p-3 bg-dark-surface rounded-lg hover:bg-dark-hover transition-colors text-left"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-300 font-medium truncate">
                  {mover.name}
                </p>
                {mover.cui && (
                  <p className="text-[10px] text-gray-600 font-mono">
                    CUI: {mover.cui}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-3">
                <span className="text-sm font-mono text-gray-400">
                  {mover.current_score}
                </span>
                <span
                  className={clsx(
                    "flex items-center gap-0.5 text-xs font-medium",
                    mover.delta < 0 ? "text-red-400" : "text-green-400",
                  )}
                >
                  {mover.delta < 0 ? (
                    <ArrowDownRight className="w-3.5 h-3.5" />
                  ) : (
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  )}
                  {mover.delta > 0 ? "+" : ""}
                  {mover.delta}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function TrendChart() {
  const [trend, setTrend] = useState<{ month: string; count: number }[]>([]);

  useEffect(() => {
    api
      .getStatsTrend()
      .then((data) => setTrend(data.trend || []))
      .catch(() => {
        /* trend chart optional — fail silently */
      });
  }, []);

  if (trend.length === 0) return null;

  const max = Math.max(...trend.map((t) => t.count), 1);
  const months = [
    "Ian",
    "Feb",
    "Mar",
    "Apr",
    "Mai",
    "Iun",
    "Iul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  const formatMonth = (m: string) => {
    const [, mm] = m.split("-");
    return months[parseInt(mm, 10) - 1] || m;
  };

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Analize pe Luna (ultimele 6 luni)
      </h2>
      <div className="flex items-end gap-3 h-32">
        {trend.map((t) => (
          <div
            key={t.month}
            className="flex-1 flex flex-col items-center gap-1"
          >
            <span className="text-xs text-gray-400 font-mono">{t.count}</span>
            <div
              className="w-full bg-accent-primary/80 rounded-t transition-all"
              style={{
                height: `${Math.max((t.count / max) * 100, 4)}%`,
                minHeight: "4px",
              }}
            />
            <span className="text-[10px] text-gray-500">
              {formatMonth(t.month)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
