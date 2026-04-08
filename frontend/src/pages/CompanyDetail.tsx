import { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  FileText,
  Shield,
  PlusCircle,
  TrendingUp,
  TrendingDown,
  Calendar,
  MapPin,
  Bell,
  ArrowUpDown,
  Users,
  Star,
  AlertTriangle,
  Loader2,
  Download,
  RefreshCw,
  MessageCircle,
  Send,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";
import { ANALYSIS_TYPE_LABELS } from "@/lib/constants";
import type { TimelineEvent, ScoringDimension } from "@/lib/types";

interface CompanyReport {
  id: string;
  report_type: string;
  report_level: number;
  title: string | null;
  summary: string | null;
  risk_score: string | null;
  created_at: string;
}

interface ScoreEntry {
  numeric_score: number | null;
  dimensions: string | null;
  recorded_at: string;
}

interface CompanyFull {
  id: string;
  cui: string | null;
  name: string;
  caen_code: string | null;
  caen_description: string | null;
  county: string | null;
  city: string | null;
  first_analyzed_at: string | null;
  last_analyzed_at: string | null;
  analysis_count: number;
  reports: CompanyReport[];
  score_history: ScoreEntry[];
}

// F2-4: SVG Sparkline pentru istoricul scorului (zero dependinte externe)
function ScoreSparkline({
  history,
}: {
  history: Array<{ numeric_score: number; recorded_at: string }>;
}) {
  if (!history || history.length < 2) return null;
  const scores = history.map((h) => h.numeric_score ?? 0);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const W = 200,
    H = 60,
    PAD = 4;
  const points = scores
    .map((s, i) => {
      const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2);
      const y = H - PAD - ((s - min) / (max - min || 1)) * (H - PAD * 2);
      return `${x},${y}`;
    })
    .join(" ");
  const last = scores[scores.length - 1];
  const color = last >= 70 ? "#22c55e" : last >= 40 ? "#eab308" : "#ef4444";
  return (
    <svg width={W} height={H} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" />
      {scores.map((s, i) => {
        const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2);
        const y = H - PAD - ((s - min) / (max - min || 1)) * (H - PAD * 2);
        return <circle key={i} cx={x} cy={y} r={3} fill={color} />;
      })}
    </svg>
  );
}

const riskBadge = (score: string | null) => {
  const map: Record<string, string> = {
    Verde: "bg-green-500/15 text-green-400 border-green-500/30",
    Galben: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    Rosu: "bg-red-500/15 text-red-400 border-red-500/30",
  };
  return map[score || ""] || "bg-gray-500/15 text-gray-400 border-gray-500/30";
};

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [company, setCompany] = useState<CompanyFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFavorite, setIsFavorite] = useState(false);
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  // F6-6: Auto re-analyze
  const [autoReanalyze, setAutoReanalyze] = useState(false);
  const [autoReanalyzeLoading, setAutoReanalyzeLoading] = useState(false);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  // F3-3: Tags & Note
  const [tags, setTags] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [newTag, setNewTag] = useState("");

  // RAG Chat
  interface ChatMessage {
    role: "user" | "assistant";
    text: string;
    provider?: string;
  }
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getCompany(id)
      .then((c) => {
        const full = c as unknown as CompanyFull;
        setCompany(full);
        // Check if is_favorite field exists (backend may return 0/1 integer or boolean)
        const maybeFav = (c as unknown as Record<string, unknown>).is_favorite;
        if (maybeFav !== undefined && maybeFav !== null)
          setIsFavorite(Boolean(maybeFav));
        logAction("CompanyDetail", "open", { companyId: id, name: full.name });
      })
      .catch(() => toast("Eroare la incarcarea companiei", "error"))
      .finally(() => setLoading(false));

    // N4: Fetch timeline
    setTimelineLoading(true);
    api
      .getCompanyTimeline(id)
      .then((res) => setTimeline(res.events ?? []))
      .catch(() => {
        /* timeline is optional */
      })
      .finally(() => setTimelineLoading(false));

    // F3-3: Fetch tags & note
    Promise.all([
      api.getCompanyTags(id).catch(() => ({ tags: [] as string[] })),
      api.getCompanyNote(id).catch(() => ({ note: "", updated_at: null })),
    ]).then(([tagsRes, noteRes]) => {
      setTags(tagsRes.tags || []);
      setNote(noteRes.note || "");
    });
  }, [id]);

  const handleToggleFavorite = () => {
    if (!id) return;
    api
      .toggleFavorite(id)
      .then((res) => {
        setIsFavorite(res.is_favorite);
        toast(
          res.is_favorite ? "Adaugat la favorite" : "Eliminat din favorite",
          "success",
        );
        logAction("CompanyDetail", "toggleFavorite", {
          companyId: id,
          isFavorite: res.is_favorite,
        });
      })
      .catch(() => toast("Eroare la actualizarea favoritelor", "error"));
  };

  const handleNewAnalysis = () => {
    if (!company?.cui) return;
    logAction("CompanyDetail", "newAnalysis", {
      companyId: id,
      cui: company.cui,
    });
    navigate(
      `/new-analysis?cui=${company.cui}&name=${encodeURIComponent(company.name)}`,
    );
  };

  // F3-3: Tag handlers
  const handleAddTag = async () => {
    const trimmed = newTag.trim();
    if (!trimmed || !id) return;
    if (tags.includes(trimmed)) {
      setNewTag("");
      return;
    }
    try {
      await api.addCompanyTag(id, trimmed);
      setTags([trimmed, ...tags]);
      setNewTag("");
    } catch {
      toast("Eroare la adaugarea tag-ului", "error");
    }
  };

  const handleRemoveTag = async (tag: string) => {
    if (!id) return;
    try {
      await api.removeCompanyTag(id, tag);
      setTags(tags.filter((t) => t !== tag));
    } catch {
      toast("Eroare la stergerea tag-ului", "error");
    }
  };

  const handleSaveNote = async () => {
    if (!id) return;
    try {
      await api.upsertCompanyNote(id, note);
      toast("Nota salvata", "success");
    } catch {
      toast("Eroare la salvarea notei", "error");
    }
  };

  const handleChat = async () => {
    const q = chatInput.trim();
    if (!q || !id || chatLoading) return;
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", text: q }]);
    setChatLoading(true);
    try {
      const res = await api.chatCompany(id, q);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, provider: res.provider },
      ]);
      setTimeout(
        () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }),
        50,
      );
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Eroare la generarea raspunsului. Incearca din nou.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-dark-card rounded w-48" />
        <div className="h-40 bg-dark-card rounded-xl" />
        <div className="h-64 bg-dark-card rounded-xl" />
      </div>
    );
  }

  if (!company) {
    return <p className="text-gray-500">Compania nu a fost gasita.</p>;
  }

  // Parse latest score from score_history (defensive: backend may omit field)
  const scoreHistory = company.score_history ?? [];
  const latestScore = scoreHistory[0];
  const prevScore = scoreHistory[1];
  const scoreDelta =
    latestScore?.numeric_score != null && prevScore?.numeric_score != null
      ? latestScore.numeric_score - prevScore.numeric_score
      : null;

  // Parse dimensions from latest score
  let dimensions: Record<string, ScoringDimension> | null = null;
  if (latestScore?.dimensions) {
    try {
      dimensions = JSON.parse(latestScore.dimensions);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <Link
          to="/companies"
          className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 mb-3"
        >
          <ArrowLeft className="w-3 h-3" /> Inapoi la companii
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
              <Building2 className="w-7 h-7 text-accent-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white">
                  {company.name}
                </h1>
                <button
                  onClick={handleToggleFavorite}
                  className="p-1 rounded hover:bg-dark-hover transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                  aria-label={
                    isFavorite ? "Elimina din favorite" : "Adauga la favorite"
                  }
                  title={
                    isFavorite ? "Sterge din favorite" : "Adauga la favorite"
                  }
                >
                  <Star
                    className={clsx(
                      "w-5 h-5 transition-colors",
                      isFavorite
                        ? "text-yellow-400 fill-yellow-400"
                        : "text-gray-600 hover:text-yellow-400",
                    )}
                  />
                </button>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-sm text-gray-500">
                {company.cui && <span>CUI: {company.cui}</span>}
                {company.caen_code && (
                  <span>
                    CAEN: {company.caen_code}
                    {company.caen_description &&
                      ` — ${company.caen_description}`}
                  </span>
                )}
                {(company.city || company.county) && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {[company.city, company.county].filter(Boolean).join(", ")}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleNewAnalysis}
              className="btn-primary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label="Porneste o noua analiza pentru aceasta firma"
            >
              <PlusCircle className="w-4 h-4" />
              Re-analiza
            </button>
            {company.cui && (
              <a
                href={`/api/companies/${company.cui}/timeline-report/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                aria-label="Descarca raport PDF cu evolutia multi-an a firmei"
                title="Genereaza PDF cu evolutia CA, Profit, Angajati si Scor Risc pe mai multi ani"
              >
                <TrendingUp className="w-4 h-4" />
                Raport Evolutie
              </a>
            )}
            <button
              onClick={() => {
                if (!company.cui) {
                  toast("CUI indisponibil", "warning");
                  return;
                }
                setMonitoringLoading(true);
                api
                  .createMonitoring({
                    company_id: company.id,
                    telegram_notify: true,
                  })
                  .then(() => toast("Monitorizare activata!", "success"))
                  .catch(() =>
                    toast("Eroare la activarea monitorizarii", "error"),
                  )
                  .finally(() => setMonitoringLoading(false));
              }}
              disabled={monitoringLoading}
              className="btn-secondary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label="Activeaza monitorizare pentru aceasta firma"
            >
              {monitoringLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Bell className="w-4 h-4" />
              )}
              {monitoringLoading ? "Se activeaza..." : "Monitorizeaza"}
            </button>
            <button
              onClick={() => {
                if (!company.cui) {
                  toast("CUI indisponibil", "warning");
                  return;
                }
                navigate(`/compare?cui=${company.cui}`);
              }}
              className="btn-secondary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label="Compara aceasta firma cu alta"
            >
              <ArrowUpDown className="w-4 h-4" />
              Compara
            </button>
            {company.caen_code && (
              <button
                onClick={() =>
                  navigate(`/companies?search=${company.caen_code}`)
                }
                className="btn-secondary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                aria-label={`Cauta firme similare cu CAEN ${company.caen_code}`}
              >
                <Users className="w-4 h-4" />
                Firme similare
              </button>
            )}
            {/* F6-6: Auto Re-analyze toggle */}
            <button
              onClick={() => {
                if (!id || autoReanalyzeLoading) return;
                setAutoReanalyzeLoading(true);
                api
                  .toggleAutoReanalyze(id)
                  .then((res) => {
                    setAutoReanalyze(res.auto_reanalyze);
                    toast(
                      res.auto_reanalyze
                        ? "Re-analiza automata activata"
                        : "Re-analiza automata dezactivata",
                      "success",
                    );
                  })
                  .catch(() =>
                    toast(
                      "Eroare la actualizarea re-analizei automate",
                      "error",
                    ),
                  )
                  .finally(() => setAutoReanalyzeLoading(false));
              }}
              disabled={autoReanalyzeLoading}
              className="btn-secondary flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              aria-label={
                autoReanalyze
                  ? "Dezactiveaza re-analiza automata"
                  : "Activeaza re-analiza automata"
              }
              title={
                autoReanalyze
                  ? "Re-analiza automata ACTIVA — click pentru dezactivare"
                  : "Activeaza re-analiza automata periodica"
              }
            >
              {autoReanalyzeLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Re-analiza Auto
              {autoReanalyze && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-semibold">
                  ACTIV
                </span>
              )}
              {!autoReanalyze && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">
                  INACTIV
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Score */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Shield className="w-5 h-5 text-gray-500 mb-1" />
          {latestScore?.numeric_score != null ? (
            <>
              <span className="text-3xl font-bold text-white font-mono">
                {latestScore.numeric_score}
              </span>
              <span className="text-xs text-gray-500">/100</span>
              {scoreDelta != null && scoreDelta !== 0 && (
                <span
                  className={clsx(
                    "text-xs flex items-center gap-0.5 mt-1",
                    scoreDelta > 0 ? "text-green-400" : "text-red-400",
                  )}
                >
                  {scoreDelta > 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  {scoreDelta > 0 ? "+" : ""}
                  {scoreDelta.toFixed(0)}
                </span>
              )}
            </>
          ) : (
            <span className="text-lg text-gray-600">N/A</span>
          )}
          <span className="text-[10px] text-gray-600 mt-1">Scor Risc</span>
        </div>

        {/* Analyses */}
        <div className="card flex flex-col items-center justify-center py-5">
          <FileText className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-3xl font-bold text-white font-mono">
            {company.analysis_count}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Analize</span>
        </div>

        {/* First analyzed */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Calendar className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-sm font-medium text-white">
            {company.first_analyzed_at
              ? new Date(company.first_analyzed_at).toLocaleDateString("ro-RO")
              : "—"}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Prima Analiza</span>
        </div>

        {/* Last analyzed */}
        <div className="card flex flex-col items-center justify-center py-5">
          <Calendar className="w-5 h-5 text-gray-500 mb-1" />
          <span className="text-sm font-medium text-white">
            {company.last_analyzed_at
              ? new Date(company.last_analyzed_at).toLocaleDateString("ro-RO")
              : "—"}
          </span>
          <span className="text-[10px] text-gray-600 mt-1">Ultima Analiza</span>
        </div>
      </div>

      {/* Dimensions Breakdown */}
      {dimensions && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
            Scor pe Dimensiuni
          </h3>
          <p className="text-[10px] text-gray-600 mb-3">
            Hover pe o dimensiune pentru a vedea explicatia scorului
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(dimensions).map(([key, dim]) => {
              const barColor =
                dim.score >= 70
                  ? "bg-green-400"
                  : dim.score >= 40
                    ? "bg-yellow-400"
                    : "bg-red-400";
              const hasReasons = dim.reasons && dim.reasons.length > 0;
              return (
                <div
                  key={key}
                  className="relative group bg-dark-surface rounded-lg p-3"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs text-gray-400 capitalize flex items-center gap-1">
                      {key}
                      {hasReasons && (
                        <span
                          className="text-gray-600 text-[9px]"
                          title="Click pentru detalii"
                        >
                          ⓘ
                        </span>
                      )}
                    </span>
                    <span className="text-sm font-mono font-medium text-gray-300">
                      {dim.score}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-dark-border rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        "h-full rounded-full transition-all",
                        barColor,
                      )}
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-600 mt-1 block">
                    Pondere: {dim.weight}%
                    {dim.confidence !== undefined && (
                      <span className="ml-2 text-gray-700">
                        Conf: {Math.round(dim.confidence * 100)}%
                      </span>
                    )}
                  </span>

                  {/* Tooltip cu reasons */}
                  {hasReasons && (
                    <div className="absolute left-0 top-full mt-1 z-30 hidden group-hover:block bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl w-72 pointer-events-none">
                      <p className="text-xs text-gray-400 mb-2 font-medium">
                        De ce {dim.score}/100:
                      </p>
                      <div className="space-y-1.5">
                        {dim.reasons!.map((r, i) => (
                          <div
                            key={i}
                            className="flex justify-between items-start gap-2 text-xs"
                          >
                            <span className="text-gray-300 flex-1 leading-tight">
                              {r.text}
                            </span>
                            {r.impact !== 0 && (
                              <span
                                className={clsx(
                                  "font-mono font-bold whitespace-nowrap shrink-0",
                                  r.impact > 0
                                    ? "text-green-400"
                                    : "text-red-400",
                                )}
                              >
                                {r.impact > 0 ? "+" : ""}
                                {r.impact}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                      {dim.insufficient_data && (
                        <p className="text-[10px] text-yellow-600 mt-2 border-t border-gray-800 pt-2">
                          Date insuficiente — scor neutralizat la 50
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Score History */}
      {scoreHistory.length > 1 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
            Istoric Scor ({scoreHistory.length} inregistrari)
          </h3>
          {/* F2-4: Sparkline SVG trend */}
          <div className="mb-4 flex items-center gap-3">
            <ScoreSparkline
              history={[...scoreHistory].reverse().map((e) => ({
                numeric_score: e.numeric_score ?? 0,
                recorded_at: e.recorded_at,
              }))}
            />
            <div className="text-xs text-gray-600 leading-relaxed">
              <p>Evolutie scor</p>
              <p className="font-mono">
                {[...scoreHistory].reverse()[0]?.numeric_score ?? "—"} →{" "}
                {scoreHistory[0]?.numeric_score ?? "—"}
              </p>
            </div>
          </div>
          <div className="flex items-end gap-1 h-24">
            {[...scoreHistory].reverse().map((entry, i) => {
              const score = entry.numeric_score ?? 0;
              const barColor =
                score >= 70
                  ? "bg-green-400"
                  : score >= 40
                    ? "bg-yellow-400"
                    : "bg-red-400";
              return (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center gap-1"
                >
                  <span className="text-[10px] text-gray-500 font-mono">
                    {score}
                  </span>
                  <div
                    className={clsx("w-full rounded-t", barColor)}
                    style={{ height: `${Math.max(score, 4)}%` }}
                    title={`${score}/100 — ${new Date(entry.recorded_at).toLocaleDateString("ro-RO")}`}
                  />
                  <span className="text-[8px] text-gray-600 truncate w-full text-center">
                    {new Date(entry.recorded_at).toLocaleDateString("ro-RO", {
                      day: "2-digit",
                      month: "short",
                    })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reports List */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase">
            Rapoarte ({(company.reports ?? []).length})
          </h3>
        </div>

        {(company.reports ?? []).length === 0 ? (
          <p className="text-gray-600 text-sm py-4 text-center">
            Niciun raport generat inca.
          </p>
        ) : (
          <div className="space-y-2">
            {(company.reports ?? []).map((report) => (
              <div
                key={report.id}
                className="flex items-center justify-between p-3 bg-dark-surface rounded-lg hover:bg-dark-hover transition-colors group"
              >
                <Link
                  to={`/report/${report.id}`}
                  className="flex items-center gap-3 flex-1 min-w-0"
                >
                  <FileText className="w-4 h-4 text-gray-500 group-hover:text-accent-secondary shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-gray-300 group-hover:text-white truncate">
                      {report.title ||
                        ANALYSIS_TYPE_LABELS[report.report_type] ||
                        report.report_type}
                    </p>
                    <p className="text-xs text-gray-600">
                      Nivel {report.report_level} |{" "}
                      {new Date(report.created_at).toLocaleDateString("ro-RO")}
                    </p>
                  </div>
                </Link>

                <div className="flex items-center gap-2 shrink-0 ml-2">
                  {/* F2-5: Download direct PDF/Excel/HTML */}
                  <div className="flex items-center gap-1">
                    <Download className="w-3 h-3 text-gray-600" />
                    {(["pdf", "excel", "html"] as const).map((fmt) => (
                      <a
                        key={fmt}
                        href={`/api/reports/${report.id}/download/${fmt}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-gray-500 hover:text-white uppercase px-1 py-0.5 rounded hover:bg-dark-border/50 transition-colors"
                        title={`Descarca ${fmt.toUpperCase()}`}
                      >
                        {fmt}
                      </a>
                    ))}
                  </div>
                  {report.risk_score && (
                    <span
                      className={clsx(
                        "text-xs font-medium px-2 py-0.5 rounded border",
                        riskBadge(report.risk_score),
                      )}
                    >
                      {report.risk_score}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* F3-3: Note & Tag-uri */}
      <div className="card space-y-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase">
          Note &amp; Tag-uri
        </h3>

        {/* Tags */}
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2 min-h-[28px]">
            {tags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 px-2 py-1 bg-accent-primary/20 text-accent-primary text-xs rounded-full"
              >
                {t}
                <button
                  onClick={() => handleRemoveTag(t)}
                  className="hover:text-white leading-none"
                  aria-label={`Sterge tag ${t}`}
                >
                  ×
                </button>
              </span>
            ))}
            {tags.length === 0 && (
              <span className="text-xs text-gray-600 italic">
                Niciun tag adaugat
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <input
              value={newTag}
              onChange={(e) => setNewTag(e.target.value.slice(0, 30))}
              onKeyDown={(e) => e.key === "Enter" && handleAddTag()}
              placeholder="Tag nou (max 30 caract.) — Enter pentru adaugare"
              maxLength={30}
              className="flex-1 bg-dark-surface border border-dark-border rounded px-2 py-1 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent-primary"
            />
            <button
              onClick={handleAddTag}
              className="btn-secondary text-sm px-3"
            >
              Adauga
            </button>
          </div>
        </div>

        {/* Nota interna */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-500">Nota interna</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value.slice(0, 2000))}
            onBlur={handleSaveNote}
            placeholder="Adauga o nota despre aceasta firma..."
            rows={3}
            maxLength={2000}
            className="w-full bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-white resize-none placeholder-gray-600 focus:outline-none focus:border-accent-primary"
          />
          <p className="text-xs text-gray-600">
            {note.length}/2000 — salvat automat la pierderea focusului
          </p>
        </div>
      </div>

      {/* N4: Timeline */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-400 uppercase mb-4">
          Timeline
        </h3>

        {timelineLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />
          </div>
        ) : timeline.length === 0 ? (
          <p className="text-gray-600 text-sm py-4 text-center">
            Nicio activitate inregistrata
          </p>
        ) : (
          <div className="relative">
            {/* Vertical line */}
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

      {/* RAG Chat with Company */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <MessageCircle className="w-4 h-4 text-accent-primary" />
          <h3 className="text-sm font-semibold text-gray-400 uppercase">
            Chat cu Compania
          </h3>
          <span className="text-xs text-gray-600 ml-auto">
            Intreaba despre datele din ultimul raport
          </span>
        </div>

        {/* Mesaje */}
        <div className="space-y-3 max-h-80 overflow-y-auto mb-3 pr-1">
          {chatMessages.length === 0 && (
            <p className="text-xs text-gray-600 italic text-center py-6">
              Pune o intrebare despre aceasta companie.
              <br />
              Ex: &ldquo;Care este riscul principal daca dau un credit de 50k
              EUR?&rdquo;
            </p>
          )}
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={clsx(
                "rounded-lg px-3 py-2 text-sm max-w-[90%]",
                msg.role === "user"
                  ? "bg-accent-primary/20 text-white ml-auto text-right"
                  : "bg-dark-surface text-gray-300",
              )}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {msg.provider && msg.role === "assistant" && (
                <p className="text-[10px] text-gray-600 mt-1">
                  via {msg.provider}
                </p>
              )}
            </div>
          ))}
          {chatLoading && (
            <div className="flex items-center gap-2 text-gray-500 text-xs">
              <Loader2 className="w-3 h-3 animate-spin" />
              Generez raspuns...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value.slice(0, 500))}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChat()}
            placeholder="Intreaba ceva despre aceasta firma..."
            maxLength={500}
            disabled={chatLoading}
            className="flex-1 bg-dark-surface border border-dark-border rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent-primary disabled:opacity-50"
          />
          <button
            onClick={handleChat}
            disabled={chatLoading || !chatInput.trim()}
            className="btn-primary px-3 py-2 disabled:opacity-50"
            aria-label="Trimite intrebare"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-gray-700 mt-1">
          {chatInput.length}/500 — Enter pentru trimitere | Necesita un raport
          generat anterior
        </p>
      </div>
    </div>
  );
}
