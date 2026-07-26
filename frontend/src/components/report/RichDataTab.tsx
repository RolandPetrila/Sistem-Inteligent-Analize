import { Link } from "react-router-dom";
import clsx from "clsx";
import { buildRichFieldsModel, type RichFieldsModel } from "@/lib/richFields";
import {
  getDueDiligenceItems,
  getEarlyWarnings,
  getCompanyNetwork,
  getKeyTakeaways,
  getWebIntelSignals,
} from "@/lib/extendedReportFields";

interface RichDataTabProps {
  fullData: Record<string, any> | null | undefined;
  cui?: string;
}

function fmtNum(v: unknown): string {
  if (typeof v !== "number" || Number.isNaN(v)) return "—";
  return v.toLocaleString("ro-RO");
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div id={id} className="p-4 bg-dark-surface rounded-lg space-y-2">
      <h4 className="text-sm font-semibold text-gray-200">{title}</h4>
      {children}
    </div>
  );
}

const SEVERITY_COLOR: Record<string, string> = {
  RED: "text-red-400 border-red-500/40",
  HIGH: "text-red-400 border-red-500/40",
  YELLOW: "text-yellow-400 border-yellow-500/40",
  MEDIUM: "text-yellow-400 border-yellow-500/40",
  INFO: "text-accent-secondary border-accent-primary/30",
  LOW: "text-blue-400 border-blue-500/30",
};

// CERINTA #4 (2026-07-26): sectiunea Garantii se randeaza INTOTDEAUNA -- linia de
// verificare manuala RNPM e neconditionata (auto-verificarea AEGRM e structural moarta).
// De aceea o randam si pe ramura `!anyShown` (fixture gol), nu doar in corpul principal.
// AEGRM/istoric raman conditionate inauntru; culoarea liniei RNPM e neutra, niciodata verde.
function GarantiiSection({ model }: { model: RichFieldsModel }) {
  return (
    <Section id="garantii" title="Garantii & Istoric (OSINT)">
      {model.garantii.aegrmOk && model.garantii.aegrm && (
        <p
          className={clsx(
            "text-sm font-medium",
            model.garantii.aegrm.has_guarantees
              ? "text-yellow-400"
              : "text-green-400",
          )}
        >
          Garantii reale mobiliare (AEGRM): {model.garantii.aegrm.count ?? 0}
        </p>
      )}
      {model.garantii.histOk && (
        <div className="space-y-1.5 mt-2">
          {model.garantii.historicalFlags.map((flx, i) =>
            flx.isDict ? (
              <div
                key={i}
                className={clsx(
                  "p-2 rounded border-l-4 bg-dark-card text-xs",
                  SEVERITY_COLOR[flx.severity] || SEVERITY_COLOR.INFO,
                )}
              >
                <strong>{flx.label}</strong>{" "}
                {flx.date && <span className="text-gray-600">{flx.date}</span>}{" "}
                <span className="text-gray-400">
                  — {flx.detail.slice(0, 240)}
                </span>
              </div>
            ) : (
              <div key={i} className="text-xs text-gray-400">
                {flx.detail}
              </div>
            ),
          )}
        </div>
      )}
      <p className="text-xs text-gray-400 mt-2">
        {model.garantii.rnpmManual}{" "}
        <a
          href={model.garantii.rnpmUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent-secondary underline"
        >
          co.rnpm.ro
        </a>
      </p>
    </Section>
  );
}

export function RichDataTab({ fullData, cui }: RichDataTabProps) {
  const model = buildRichFieldsModel(fullData ?? {});
  const dueDiligence = getDueDiligenceItems(fullData);
  const earlyWarnings = getEarlyWarnings(fullData);
  const network = getCompanyNetwork(fullData);
  const keyTakeaways = getKeyTakeaways(fullData);
  const { mapsRating, freshness } = getWebIntelSignals(fullData);

  const anyShown =
    keyTakeaways ||
    model.sanctions.shown ||
    model.actionariat.shown ||
    model.garantii.shown ||
    earlyWarnings.length > 0 ||
    dueDiligence.length > 0 ||
    model.benchmark.shown ||
    model.eurostatSector.shown ||
    model.seap.shown ||
    model.tenderOpportunities.shown ||
    model.fundingPrograms.shown ||
    model.creditExposure.shown ||
    !!network ||
    !!mapsRating ||
    !!freshness;

  if (!anyShown) {
    // Chiar si fara alte date extinse, linia de verificare manuala RNPM apare
    // NECONDITIONAT (CERINTA #4) -- auto-verificarea garantiilor mobiliare e moarta.
    return (
      <div className="space-y-3">
        <p className="text-xs text-gray-500 italic">
          Nu exista date extinse (due-diligence, sanctiuni, actionariat,
          benchmark, licitatii, retea) pentru acest raport.
        </p>
        <GarantiiSection model={model} />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-400 uppercase mb-1">
        Date Extinse (Due Diligence)
      </h3>

      {keyTakeaways && (
        <Section id="key-takeaways" title="Concluzii Cheie">
          <div className="text-sm text-gray-300 whitespace-pre-wrap">
            {keyTakeaways}
          </div>
        </Section>
      )}

      {earlyWarnings.length > 0 && (
        <Section id="early-warnings" title="Semnale de Avertizare">
          <div className="space-y-2">
            {earlyWarnings.map((ew, i) => (
              <div
                key={i}
                className={clsx(
                  "p-2.5 rounded border-l-4 bg-dark-card flex items-start justify-between gap-3",
                  SEVERITY_COLOR[ew.severity] || SEVERITY_COLOR.INFO,
                )}
              >
                <span className="text-sm text-gray-300">{ew.warning}</span>
                <span className="text-xs text-gray-500 shrink-0">
                  incredere {ew.confidence}%
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {dueDiligence.length > 0 && (
        <Section
          id="due-diligence"
          title={`Checklist Due Diligence (${dueDiligence.filter((d) => d.status === "DA").length}/${dueDiligence.length})`}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {dueDiligence.map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-xs p-2 bg-dark-card rounded"
              >
                <span className="text-gray-300">{item.name}</span>
                <span
                  className={clsx(
                    "font-mono font-bold px-1.5 rounded",
                    item.status === "DA"
                      ? "text-green-400"
                      : item.status === "NU"
                        ? "text-red-400"
                        : "text-gray-500",
                  )}
                >
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {model.sanctions.shown && (
        <Section id="sanctions" title="Screening Sanctiuni">
          {model.sanctions.data.status === "clean" ? (
            <p className="text-sm text-green-400 font-medium">
              CURAT — {(model.sanctions.data.checked || []).length} nume
              verificate, 0 potriviri pe OFAC/UE/ONU
            </p>
          ) : model.sanctions.data.status === "hit" ? (
            <>
              <p className="text-sm text-red-400 font-bold">
                {(model.sanctions.data.hits || []).length} potentiale potriviri
                — verificare manuala necesara
              </p>
              <ul className="list-disc ml-5 text-xs text-gray-400 space-y-0.5">
                {(model.sanctions.data.hits || [])
                  .slice(0, 20)
                  .map((h: any, i: number) => (
                    <li key={i}>
                      <strong className="text-gray-300">{h.query}</strong> ≈{" "}
                      {h.matched_name}{" "}
                      <span className="text-gray-500">
                        [{h.source}, {h.type}]
                      </span>
                    </li>
                  ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-gray-500 italic">
              Screening indisponibil (liste temporar inaccesibile).
            </p>
          )}
          <p className="text-[10px] text-gray-600 italic">
            Nu include PEP (persoane expuse politic).
          </p>
        </Section>
      )}

      {model.actionariat.shown && (
        <Section id="actionariat" title="Actionariat & Relatii">
          {model.actionariat.actOk && (
            <>
              {(model.actionariat.act.capital_social ||
                model.actionariat.act.stare) && (
                <p className="text-sm text-gray-300">
                  {model.actionariat.act.capital_social && (
                    <>
                      Capital social:{" "}
                      <strong>
                        {fmtNum(model.actionariat.act.capital_social)}
                      </strong>{" "}
                    </>
                  )}
                  {model.actionariat.act.stare && (
                    <span className="text-gray-500">
                      Stare: {model.actionariat.act.stare}
                    </span>
                  )}
                </p>
              )}
              {["asociati", "administratori"].map((k) => {
                const items = model.actionariat.act[k];
                if (!Array.isArray(items) || items.length === 0) return null;
                return (
                  <div key={k}>
                    <p className="text-xs text-gray-500 uppercase mt-2 mb-1">
                      {k === "asociati" ? "Asociati" : "Administratori"}
                    </p>
                    <ul className="list-disc ml-5 text-xs text-gray-300 space-y-0.5">
                      {items.map((it: any, i: number) => (
                        <li key={i}>
                          {typeof it === "object"
                            ? it.nume ||
                              it.name ||
                              it.denumire ||
                              JSON.stringify(it)
                            : String(it)}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </>
          )}
          {model.actionariat.relFlags.length > 0 && (
            <div className="space-y-1.5 mt-2">
              {model.actionariat.relFlags.map((fl: any, i: number) => (
                <div
                  key={i}
                  className={clsx(
                    "p-2 rounded border-l-4 bg-dark-card text-xs",
                    SEVERITY_COLOR[String(fl.severity).toUpperCase()] ||
                      SEVERITY_COLOR.INFO,
                  )}
                >
                  <strong>{fl.type}</strong>{" "}
                  <span className="text-gray-400">— {fl.detail}</span>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <GarantiiSection model={model} />

      {model.benchmark.shown && (
        <Section
          id="benchmark"
          title={`Benchmark Sector CAEN ${model.benchmark.data.caen_code || ""}`}
        >
          {model.benchmark.data.caen_section_name && (
            <p className="text-xs text-gray-500">
              {model.benchmark.data.caen_section_name} —{" "}
              {model.benchmark.data.nr_firme_sector ?? "?"} firme in sector
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs mt-1">
              <thead>
                <tr className="text-gray-500 text-left">
                  <th className="py-1">Indicator</th>
                  <th className="py-1 text-right">Firma</th>
                  <th className="py-1 text-right">Media sector</th>
                  <th className="py-1 text-center">Pozitie</th>
                </tr>
              </thead>
              <tbody>
                {(model.benchmark.data.comparisons || []).map(
                  (c: any, i: number) => (
                    <tr key={i} className="border-t border-dark-border">
                      <td className="py-1.5 text-gray-300">{c.metric}</td>
                      <td className="py-1.5 text-right text-accent-secondary">
                        {fmtNum(c.firma)}
                      </td>
                      <td className="py-1.5 text-right text-gray-400">
                        {fmtNum(c.media_sector)}
                      </td>
                      <td className="py-1.5 text-center text-gray-300">
                        {c.pozitie}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {model.eurostatSector.shown && (
        <Section id="eurostat" title="Benchmark Sector UE (Eurostat)">
          <p className="text-xs text-gray-500">
            Sector NACE {model.eurostatSector.data.nace_used} —{" "}
            {model.eurostatSector.data.nace_label} — an{" "}
            {model.eurostatSector.data.year}
          </p>
          <table className="w-full text-xs mt-1">
            <thead>
              <tr className="text-gray-500 text-left">
                <th className="py-1">Indicator</th>
                <th className="py-1 text-right">Romania</th>
                <th className="py-1 text-right">UE27</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(model.eurostatSector.data.indicators || {}).map(
                (ind: any, i: number) => (
                  <tr key={i} className="border-t border-dark-border">
                    <td className="py-1.5 text-gray-300">{ind.label}</td>
                    <td className="py-1.5 text-right text-gray-200">
                      {fmtNum(ind.ro)}
                    </td>
                    <td className="py-1.5 text-right text-gray-200">
                      {fmtNum(ind.eu)}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
          <p className="text-[10px] text-gray-600">Sursa: Eurostat (SBS).</p>
        </Section>
      )}

      {model.seap.shown && (
        <Section id="achizitii" title="Istoric Achizitii Publice (SICAP)">
          <p className="text-sm text-green-400 font-medium">
            {model.seap.data.total_contracts || 0} contracte publice castigate
            {typeof model.seap.data.total_value === "number" &&
              ` · valoare totala ~${fmtNum(model.seap.data.total_value)} RON`}
          </p>
          <ul className="list-disc ml-5 text-xs text-gray-300 space-y-1 mt-1">
            {(model.seap.data.contracts || [])
              .slice(0, 8)
              .map((c: any, i: number) => (
                <li key={i}>
                  <strong>{String(c.title || "").slice(0, 120)}</strong>
                  {c.authority && <> — {c.authority}</>}
                  {typeof c.value === "number" && (
                    <>
                      {" "}
                      · {fmtNum(c.value)} {c.currency || "RON"}
                    </>
                  )}
                </li>
              ))}
          </ul>
        </Section>
      )}

      {model.tenderOpportunities.shown && (
        <Section id="oportunitati" title="Oportunitati de Contracte (SICAP)">
          <p className="text-xs text-gray-500">
            {model.tenderOpportunities.data.count || 0} licitatii deschise
            (ultimele {model.tenderOpportunities.data.days_back || 30} zile)
          </p>
          <ul className="list-disc ml-5 text-xs text-gray-300 space-y-1 mt-1">
            {(model.tenderOpportunities.data.opportunities || [])
              .slice(0, 15)
              .map((it: any, i: number) => (
                <li key={i}>
                  {it.precise && (
                    <span
                      className="text-green-400"
                      title="competenta dovedita"
                    >
                      ✓{" "}
                    </span>
                  )}
                  <strong>{String(it.title || "").slice(0, 120)}</strong>
                  {it.authority && <> — {it.authority}</>}
                  {typeof it.value === "number" && (
                    <> · {fmtNum(it.value)} RON</>
                  )}
                  {it.deadline && (
                    <> · termen {String(it.deadline).slice(0, 10)}</>
                  )}
                </li>
              ))}
          </ul>
        </Section>
      )}

      {model.fundingPrograms.shown && (
        <Section id="funding" title="Programe de Finantare Eligibile">
          {model.fundingPrograms.data.summary && (
            <p className="text-xs text-gray-400">
              {model.fundingPrograms.data.summary}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs mt-1">
              <thead>
                <tr className="text-gray-500 text-left">
                  <th className="py-1">Program</th>
                  <th className="py-1 text-right">Suma max</th>
                  <th className="py-1">Termen</th>
                </tr>
              </thead>
              <tbody>
                {(model.fundingPrograms.data.eligible || []).map(
                  (p: any, i: number) => (
                    <tr key={i} className="border-t border-dark-border">
                      <td className="py-1.5 text-gray-300">
                        {p.link ? (
                          <a
                            href={p.link}
                            target="_blank"
                            rel="noopener"
                            className="text-accent-secondary hover:text-white"
                          >
                            {p.nume}
                          </a>
                        ) : (
                          p.nume
                        )}
                      </td>
                      <td className="py-1.5 text-right text-green-400 font-medium">
                        {typeof p.suma_max_eur === "number" && p.suma_max_eur
                          ? `${fmtNum(p.suma_max_eur)} EUR`
                          : "—"}
                      </td>
                      <td className="py-1.5 text-gray-500">
                        {p.termen || "—"}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {model.creditExposure.shown && (
        <Section id="bonitate" title="Bonitate & Expunere Comerciala">
          <p
            className={clsx(
              "text-xl font-bold",
              model.creditExposure.data.kill_switch
                ? "text-red-400"
                : "text-green-400",
            )}
          >
            {fmtNum(model.creditExposure.data.expunere_ron)} RON
          </p>
          <p className="text-xs text-gray-500">
            {model.creditExposure.data.formula} ·{" "}
            {model.creditExposure.data.metode_folosite} metode folosite
          </p>
          {model.creditExposure.data.disclaimer && (
            <p className="text-[10px] text-gray-600 italic">
              {model.creditExposure.data.disclaimer}
            </p>
          )}
        </Section>
      )}

      {network && (
        <Section id="network" title="Retea de Firme">
          <div className="flex gap-4 flex-wrap text-xs mb-1">
            <span className="text-gray-400">
              {network.total_connected ??
                network.related_companies?.length ??
                0}{" "}
              firme conexe
            </span>
            <span className="text-gray-400">
              {network.persons?.length ?? 0} persoane comune
            </span>
            {(network.stats?.inactive ?? 0) > 0 && (
              <span className="text-red-400">
                {network.stats?.inactive} inactive
              </span>
            )}
          </div>
          {(network.risk_flags?.length ?? 0) > 0 && (
            <div className="space-y-1.5 mb-2">
              {network.risk_flags!.map((fl, i) => (
                <div
                  key={i}
                  className={clsx(
                    "p-2 rounded border-l-4 bg-dark-card text-xs",
                    SEVERITY_COLOR[fl.severity] || SEVERITY_COLOR.INFO,
                  )}
                >
                  <strong>{fl.type}</strong>{" "}
                  <span className="text-gray-400">— {fl.detail}</span>
                </div>
              ))}
            </div>
          )}
          {cui && (
            <Link
              to={`/network/${cui}`}
              className="text-xs text-accent-secondary hover:text-white inline-block mt-1"
            >
              → Vezi graful interactiv complet
            </Link>
          )}
        </Section>
      )}

      {(mapsRating || freshness) && (
        <Section id="web-intel" title="Semnale Online & Prospetime Date">
          {mapsRating && (
            <p className="text-xs text-gray-300">
              Google Maps: <strong>{mapsRating.name}</strong> —{" "}
              {mapsRating.rating}/5 ({mapsRating.reviews_count} recenzii)
              {mapsRating.address && (
                <span className="text-gray-500"> · {mapsRating.address}</span>
              )}
            </p>
          )}
          {freshness && (
            <div className="flex flex-wrap gap-2 mt-1">
              {Object.entries(freshness).map(([src, f]) => (
                <span
                  key={src}
                  className={clsx(
                    "text-[10px] px-2 py-0.5 rounded-full border",
                    f.fresh
                      ? "text-green-400 border-green-500/30"
                      : "text-yellow-400 border-yellow-500/30",
                  )}
                >
                  {src}: {f.data_age_years ?? 0}a
                </span>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
