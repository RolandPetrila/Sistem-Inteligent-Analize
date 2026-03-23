import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Building2,
  Swords,
  ShieldCheck,
  FileText,
  Banknote,
  TrendingUp,
  Users,
  Bell,
  Sparkles,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { validateCUI } from "@/lib/cui-validator";
import type { AnalysisTypeInfo } from "@/lib/types";
import { REPORT_LEVEL_LABELS } from "@/lib/constants";
import ChatInput from "@/components/ChatInput";

// E4: Quick analysis templates
const ANALYSIS_TEMPLATES = [
  { name: "Due Diligence Partener", type: "PARTNER_RISK_ASSESSMENT", level: 3, description: "Verificare completa partener de afaceri" },
  { name: "Screening Rapid", type: "CUSTOM_REPORT", level: 1, description: "Verificare rapida, date de baza" },
  { name: "Raport Complet Vanzare", type: "FULL_COMPANY_PROFILE", level: 3, description: "Raport complet pentru prezentare client" },
  { name: "Analiza Competitie", type: "COMPETITION_ANALYSIS", level: 2, description: "Focus pe competitori si pozitionare" },
  { name: "Oportunitati Licitatii", type: "TENDER_OPPORTUNITIES", level: 2, description: "Licitatii SEAP relevante" },
];

const ICONS: Record<string, React.ElementType> = {
  Building2,
  Swords,
  ShieldCheck,
  FileText,
  Banknote,
  TrendingUp,
  Users,
  Bell,
  Sparkles,
};

type Step = "type" | "questions" | "level" | "confirm";

export default function NewAnalysis() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [types, setTypes] = useState<AnalysisTypeInfo[]>([]);
  const [step, setStep] = useState<Step>("type");
  const [selected, setSelected] = useState<AnalysisTypeInfo | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [level, setLevel] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [cuiError, setCuiError] = useState("");

  // N4: Pre-fill CUI from URL params (re-analiza from CompanyDetail)
  const [searchParams] = useSearchParams();

  useEffect(() => {
    api.getAnalysisTypes().then((loaded) => {
      setTypes(loaded);
      // Auto-select FULL_COMPANY_PROFILE and pre-fill CUI if provided
      const cuiParam = searchParams.get("cui");
      if (cuiParam && loaded.length > 0) {
        const fullProfile = loaded.find((t) => t.type === "FULL_COMPANY_PROFILE");
        if (fullProfile) {
          setSelected(fullProfile);
          setAnswers({ cui: cuiParam });
          setStep(fullProfile.questions.length > 0 ? "questions" : "level");
        }
      }
    }).catch(() => toast("Eroare la incarcarea tipurilor de analiza", "error"));
  }, []);

  const handleSelectType = (t: AnalysisTypeInfo) => {
    if (t.deferred) return;
    setSelected(t);
    setAnswers({});
    setFormErrors({});
    setStep(t.questions.length > 0 ? "questions" : "level");
  };

  // 10F M12.1: Form validation — validate required fields + CUI before proceeding
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    if (!selected) return false;
    const errors: Record<string, string> = {};
    for (const q of selected.questions) {
      const val = (answers[q.id] || "").trim();
      if (q.required && !val) {
        errors[q.id] = "Camp obligatoriu";
      }
      if (q.id === "cui" && val) {
        const result = validateCUI(val);
        if (!result.valid) {
          errors[q.id] = result.error || "CUI invalid";
        }
      }
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const canProceedFromQuestions = (): boolean => {
    if (!selected) return false;
    return selected.questions
      .filter((q) => q.required)
      .every((q) => (answers[q.id] || "").trim() !== "") && !cuiError;
  };

  const handleSubmit = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      const job = await api.createJob({
        analysis_type: selected.type,
        report_level: level,
        input_params: answers,
      });
      // Auto-start the job
      await api.startJob(job.id).catch(() => toast("Job creat, dar pornirea automata a esuat", "warning"));
      navigate(`/analysis/${job.id}`);
    } catch {
      toast("Eroare la pornirea analizei", "error");
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Analiza Noua</h1>
        <p className="text-sm text-gray-500 mt-1">
          {step === "type" && "Selecteaza tipul de analiza"}
          {step === "questions" && `${selected?.name} - Completeaza detaliile`}
          {step === "level" && "Selecteaza nivelul raportului"}
          {step === "confirm" && "Confirma si porneste analiza"}
        </p>
      </div>

      {/* Chatbot Input */}
      {step === "type" && (
        <ChatInput
          onParsed={(result) => {
            const found = types.find((t) => t.type === result.analysis_type);
            if (found) {
              setSelected(found);
              setAnswers(result.input_params);
              setStep(found.questions.length > 0 ? "questions" : "level");
            }
          }}
        />
      )}

      {/* E4: Quick Templates */}
      {step === "type" && types.length > 0 && (
        <div>
          <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">Template rapid</h3>
          <div className="flex flex-wrap gap-2 mb-6">
            {ANALYSIS_TEMPLATES.map((tmpl) => (
              <button
                key={tmpl.name}
                onClick={() => {
                  const found = types.find((t) => t.type === tmpl.type);
                  if (found) {
                    setSelected(found);
                    setLevel(tmpl.level);
                    setAnswers({});
                    setFormErrors({});
                    setStep(found.questions.length > 0 ? "questions" : "level");
                  }
                }}
                className="px-3 py-1.5 text-xs rounded-lg bg-dark-surface border border-dark-border text-gray-400 hover:border-accent-primary/50 hover:text-accent-secondary transition-all"
                title={tmpl.description}
              >
                {tmpl.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step: Select Type */}
      {step === "type" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {types.map((t) => {
            const Icon = ICONS[t.icon] || Sparkles;
            return (
              <button
                key={t.type}
                onClick={() => handleSelectType(t)}
                disabled={t.deferred}
                className={clsx(
                  "card text-left transition-all duration-200 group",
                  t.deferred
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:border-accent-primary/50 hover:shadow-lg hover:shadow-accent-primary/5 cursor-pointer"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-accent-secondary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white text-sm">
                      {t.name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                      {t.description}
                    </p>
                    <div className="flex items-center gap-3 mt-3">
                      <span className="text-[10px] text-gray-600">
                        Fezabilitate: {t.feasibility}%
                      </span>
                      {t.deferred && (
                        <span className="text-[10px] text-yellow-500">
                          DISPONIBIL ULTERIOR
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Step: Questions */}
      {step === "questions" && selected && (
        <div className="card max-w-2xl space-y-5">
          {selected.questions.map((q) => (
            <div key={q.id}>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                {q.label}
                {q.required && <span className="text-red-400 ml-1">*</span>}
              </label>
              {q.type === "select" && q.options ? (
                <select
                  className="input-field w-full"
                  value={answers[q.id] || ""}
                  onChange={(e) =>
                    setAnswers({ ...answers, [q.id]: e.target.value })
                  }
                >
                  <option value="">-- Selecteaza --</option>
                  {q.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : q.type === "textarea" ? (
                <textarea
                  className="input-field w-full h-24 resize-none"
                  value={answers[q.id] || ""}
                  onChange={(e) =>
                    setAnswers({ ...answers, [q.id]: e.target.value })
                  }
                  placeholder={q.label}
                />
              ) : (
                <div>
                  <input
                    type="text"
                    className={clsx(
                      "input-field w-full",
                      q.id === "cui" && cuiError && "border-red-500/50"
                    )}
                    value={answers[q.id] || ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      setAnswers({ ...answers, [q.id]: val });
                      if (q.id === "cui" && val.replace(/\D/g, "").length >= 2) {
                        const result = validateCUI(val);
                        setCuiError(result.valid ? "" : result.error || "");
                      } else if (q.id === "cui") {
                        setCuiError("");
                      }
                    }}
                    placeholder={q.label}
                  />
                  {q.id === "cui" && cuiError && (
                    <p className="text-xs text-red-400 mt-1">{cuiError}</p>
                  )}
                  {q.id === "cui" && answers[q.id] && !cuiError && answers[q.id].replace(/\D/g, "").length >= 2 && (
                    <p className="text-xs text-green-400 mt-1">CUI valid</p>
                  )}
                  {/* 10F M12.1: Form validation error per field */}
                  {q.id !== "cui" && formErrors[q.id] && (
                    <p className="text-xs text-red-400 mt-1">{formErrors[q.id]}</p>
                  )}
                </div>
              )}
            </div>
          ))}
          <div className="flex justify-between pt-3">
            <button
              className="btn-secondary flex items-center gap-2"
              onClick={() => setStep("type")}
            >
              <ArrowLeft className="w-4 h-4" /> Inapoi
            </button>
            <button
              className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={!canProceedFromQuestions()}
              onClick={() => {
                if (validateForm()) setStep("level");
              }}
            >
              Continua <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Level */}
      {step === "level" && (
        <div className="max-w-2xl space-y-4">
          {[1, 2, 3].map((lv) => {
            const info = REPORT_LEVEL_LABELS[lv];
            const time = selected?.time_estimate[lv] || "N/A";
            return (
              <button
                key={lv}
                onClick={() => setLevel(lv)}
                className={clsx(
                  "card w-full text-left transition-all",
                  level === lv
                    ? "border-accent-primary ring-1 ring-accent-primary/30"
                    : "hover:border-dark-hover"
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white">
                      Nivel {lv} — {info.name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {info.description}
                    </p>
                  </div>
                  <span className="text-sm text-gray-400">{time}</span>
                </div>
              </button>
            );
          })}
          <div className="flex justify-between pt-3">
            <button
              className="btn-secondary flex items-center gap-2"
              onClick={() =>
                setStep(
                  selected && selected.questions.length > 0
                    ? "questions"
                    : "type"
                )
              }
            >
              <ArrowLeft className="w-4 h-4" /> Inapoi
            </button>
            <button
              className="btn-primary flex items-center gap-2"
              onClick={() => setStep("confirm")}
            >
              Continua <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Confirm */}
      {step === "confirm" && selected && (
        <div className="card max-w-2xl space-y-5">
          <h2 className="text-lg font-semibold text-white">
            Confirma Analiza
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-dark-border">
              <span className="text-gray-500">Tip Analiza</span>
              <span className="text-white font-medium">{selected.name}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-dark-border">
              <span className="text-gray-500">Nivel Raport</span>
              <span className="text-white font-medium">
                Nivel {level} — {REPORT_LEVEL_LABELS[level]?.name}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-dark-border">
              <span className="text-gray-500">Timp Estimat</span>
              <span className="text-white">
                {selected.time_estimate[level] || "N/A"}
              </span>
            </div>
            {Object.entries(answers).map(([key, val]) => {
              if (!val) return null;
              const question = selected.questions.find((q) => q.id === key);
              return (
                <div
                  key={key}
                  className="flex justify-between py-2 border-b border-dark-border"
                >
                  <span className="text-gray-500">
                    {question?.label || key}
                  </span>
                  <span className="text-white text-right max-w-xs truncate">
                    {val}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between pt-3">
            <button
              className="btn-secondary flex items-center gap-2"
              onClick={() => setStep("level")}
            >
              <ArrowLeft className="w-4 h-4" /> Inapoi
            </button>
            <button
              className="btn-primary flex items-center gap-2"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? "Se porneste..." : "Porneste Analiza"}
              {!submitting && <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
