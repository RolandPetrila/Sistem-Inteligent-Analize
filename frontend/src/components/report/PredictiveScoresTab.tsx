import clsx from "clsx";

interface AltmanZ {
  z_score: number | null;
  zone: string;
  disclaimer?: string;
}

interface PiotroskiF {
  f_score: number | null;
  max_possible?: number;
  grade: string;
}

interface BeneishM {
  m_score: number | null;
  risk: string;
  available: boolean;
}

interface ZmijewskiX {
  x_score: number | null;
  distress: boolean | null;
  available: boolean;
}

interface PredictiveScores {
  altman_z?: AltmanZ;
  piotroski_f?: PiotroskiF;
  beneish_m?: BeneishM;
  zmijewski_x?: ZmijewskiX;
  distress_signals: number;
  summary: string;
}

interface PredictiveScoresTabProps {
  loading: boolean;
  scores: PredictiveScores | null;
}

export function PredictiveScoresTab({
  loading,
  scores,
}: PredictiveScoresTabProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
        Scoruri Predictive Financiare
      </h3>

      {loading && (
        <div className="card animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-1/3 mb-2" />
          <div className="h-6 bg-gray-700 rounded w-1/2" />
        </div>
      )}

      {!loading && !scores && (
        <div className="card text-center py-6">
          <p className="text-gray-500 text-sm">
            Date predictive indisponibile pentru acest raport
          </p>
        </div>
      )}

      {!loading && scores && (
        <div className="space-y-3">
          {/* Summary badge */}
          <div
            className={clsx(
              "p-3 rounded-lg border text-sm",
              scores.distress_signals >= 3
                ? "border-red-600 bg-red-900/20 text-red-300"
                : scores.distress_signals >= 2
                  ? "border-yellow-600 bg-yellow-900/20 text-yellow-300"
                  : scores.distress_signals >= 1
                    ? "border-yellow-700 bg-yellow-900/10 text-yellow-400"
                    : "border-green-700 bg-green-900/10 text-green-400",
            )}
          >
            <strong>Concluzie:</strong> {scores.summary}
            {scores.distress_signals > 0 && (
              <span className="ml-2 text-xs">
                ({scores.distress_signals} semnale de distres)
              </span>
            )}
          </div>

          {/* 4 model cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Altman Z */}
            {scores.altman_z && (
              <div className="p-4 bg-dark-surface rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-300">
                    Altman Z''-EMS
                  </h4>
                  <span
                    className={clsx(
                      "px-2 py-0.5 text-xs rounded font-medium",
                      scores.altman_z.zone === "SAFE"
                        ? "bg-green-900 text-green-300"
                        : scores.altman_z.zone === "GREY"
                          ? "bg-yellow-900 text-yellow-300"
                          : scores.altman_z.zone === "DISTRESS"
                            ? "bg-red-900 text-red-300"
                            : "bg-gray-700 text-gray-400",
                    )}
                  >
                    {scores.altman_z.zone || "N/A"}
                  </span>
                </div>
                <p className="text-2xl font-bold font-mono text-white">
                  {scores.altman_z.z_score ?? "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Predictie insolventa (Safe &gt;2.60)
                </p>
                {scores.altman_z.disclaimer && (
                  <p className="text-xs text-gray-600 mt-2 italic">
                    {scores.altman_z.disclaimer}
                  </p>
                )}
              </div>
            )}

            {/* Piotroski F */}
            {scores.piotroski_f && (
              <div className="p-4 bg-dark-surface rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-300">
                    Piotroski F-Score
                  </h4>
                  <span
                    className={clsx(
                      "px-2 py-0.5 text-xs rounded font-medium",
                      scores.piotroski_f.grade === "STRONG"
                        ? "bg-green-900 text-green-300"
                        : scores.piotroski_f.grade === "AVERAGE"
                          ? "bg-yellow-900 text-yellow-300"
                          : scores.piotroski_f.grade === "WEAK"
                            ? "bg-red-900 text-red-300"
                            : "bg-gray-700 text-gray-400",
                    )}
                  >
                    {scores.piotroski_f.grade || "N/A"}
                  </span>
                </div>
                <p className="text-2xl font-bold font-mono text-white">
                  {scores.piotroski_f.f_score ?? "—"}
                  <span className="text-sm text-gray-500 ml-1">
                    / {scores.piotroski_f.max_possible ?? 9}
                  </span>
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Sanatate financiara (Strong ≥7)
                </p>
              </div>
            )}

            {/* Beneish M */}
            {scores.beneish_m && (
              <div className="p-4 bg-dark-surface rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-300">
                    Beneish M-Score
                  </h4>
                  <span
                    className={clsx(
                      "px-2 py-0.5 text-xs rounded font-medium",
                      !scores.beneish_m.available
                        ? "bg-gray-700 text-gray-400"
                        : scores.beneish_m.risk === "OK"
                          ? "bg-green-900 text-green-300"
                          : scores.beneish_m.risk === "INVESTIGAT"
                            ? "bg-yellow-900 text-yellow-300"
                            : "bg-red-900 text-red-300",
                    )}
                  >
                    {scores.beneish_m.available
                      ? scores.beneish_m.risk || "N/A"
                      : "INDISPONIBIL"}
                  </span>
                </div>
                <p className="text-2xl font-bold font-mono text-white">
                  {scores.beneish_m.m_score?.toFixed(2) ?? "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Detectie manipulare contabila
                </p>
                {!scores.beneish_m.available && (
                  <p className="text-xs text-gray-600 mt-1 italic">
                    Necesita 2 ani de bilant
                  </p>
                )}
              </div>
            )}

            {/* Zmijewski X */}
            {scores.zmijewski_x && (
              <div className="p-4 bg-dark-surface rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-300">
                    Zmijewski X-Score
                  </h4>
                  <span
                    className={clsx(
                      "px-2 py-0.5 text-xs rounded font-medium",
                      !scores.zmijewski_x.available
                        ? "bg-gray-700 text-gray-400"
                        : scores.zmijewski_x.distress
                          ? "bg-red-900 text-red-300"
                          : "bg-green-900 text-green-300",
                    )}
                  >
                    {!scores.zmijewski_x.available
                      ? "N/A"
                      : scores.zmijewski_x.distress
                        ? "DISTRES"
                        : "STABIL"}
                  </span>
                </div>
                <p className="text-2xl font-bold font-mono text-white">
                  {scores.zmijewski_x.x_score?.toFixed(2) ?? "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Probabilitate distres (X &gt;0 = risc)
                </p>
              </div>
            )}
          </div>

          <p className="text-xs text-gray-600 italic text-center">
            Modele predictive calibrate pe piata americana — interpretati cu
            prudenta pentru firme romanesti
          </p>
        </div>
      )}
    </div>
  );
}
