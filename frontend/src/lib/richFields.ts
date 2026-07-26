/**
 * Oglinda TypeScript a backend/reports/rich_fields.py::build_rich_fields_model().
 *
 * Acel modul e sursa canonica de gate-uri (ce inseamna "sectiunea are date
 * suficiente cat sa merite afisata") + normalizare pentru html/pdf/docx
 * generator. Randarea ramane separata pe fiecare consumator; gate-urile si
 * normalizarea historical_flags (label-peste-type, snippet-peste-detail —
 * zona care a produs bug-uri reale in 2026-06-27) trebuie sa ramana
 * IDENTICE cu Python. Schimba ambele fisiere impreuna, niciodata doar unul.
 */

export interface HistoricalFlagNormalized {
  isDict: boolean;
  label: string;
  detail: string;
  date: string;
  severity: string;
}

// CERINTA #4 (2026-07-26): oglinda constantelor RNPM_MANUAL_* din rich_fields.py.
// Auto-verificarea AEGRM e structural moarta -> linia de verificare manuala RNPM apare
// NECONDITIONAT in raport + tabul RichDataTab (scraping interzis: reCAPTCHA per-cautare).
export const RNPM_MANUAL_URL = "https://co.rnpm.ro";
export const RNPM_MANUAL_MESSAGE =
  "Garantii reale mobiliare (RNPM/AEGRM): verificare automata indisponibila " +
  "(portal protejat anti-bot). Verifica manual la";

export interface RichFieldsModel {
  predictiveScores: { shown: boolean; data: Record<string, any> };
  benchmark: { shown: boolean; data: Record<string, any> };
  eurostatSector: { shown: boolean; data: Record<string, any> };
  seap: { shown: boolean; data: Record<string, any> };
  tenderOpportunities: { shown: boolean; data: Record<string, any> };
  actionariat: {
    shown: boolean;
    actOk: boolean;
    act: Record<string, any>;
    relFlags: Record<string, any>[];
  };
  sanctions: { shown: boolean; data: Record<string, any> };
  garantii: {
    shown: boolean;
    aegrmOk: boolean;
    aegrm: Record<string, any> | undefined;
    histOk: boolean;
    historicalFlags: HistoricalFlagNormalized[];
    rnpmUrl: string;
    rnpmManual: string;
  };
  fundingPrograms: { shown: boolean; data: Record<string, any> };
  creditExposure: { shown: boolean; data: Record<string, any> };
}

function isPlainObject(v: unknown): v is Record<string, any> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

export function buildRichFieldsModel(
  verifiedData: Record<string, any> | null | undefined,
): RichFieldsModel {
  const vd = isPlainObject(verifiedData) ? verifiedData : {};

  const pred = isPlainObject(vd.predictive_scores) ? vd.predictive_scores : {};
  const hasPred = Boolean(pred.summary);

  const bench = isPlainObject(vd.benchmark) ? vd.benchmark : {};
  const hasBench =
    Boolean(bench.available) &&
    Array.isArray(bench.comparisons) &&
    bench.comparisons.length > 0;

  const eust = isPlainObject(vd.eurostat_sector) ? vd.eurostat_sector : {};
  const hasEust = Boolean(eust.available) && isPlainObject(eust.indicators);

  const market = isPlainObject(vd.market) ? vd.market : {};
  const seapField = isPlainObject(market.seap) ? market.seap : {};
  const seap = isPlainObject(seapField) ? (seapField.value ?? seapField) : {};
  const hasSeap =
    isPlainObject(seap) && (Number(seap.total_contracts) || 0) > 0;

  const opp = isPlainObject(vd.tender_opportunities)
    ? vd.tender_opportunities
    : {};
  const hasOpp = Boolean(opp.available) && Boolean(opp.count);

  const act = isPlainObject(vd.actionariat) ? vd.actionariat : {};
  const rel = isPlainObject(vd.relations) ? vd.relations : {};
  const actOk = Boolean(act.available);
  const relFlags = Array.isArray(rel.flags) ? rel.flags : [];
  const hasActionariat = actOk || relFlags.length > 0;

  const sanc = isPlainObject(vd.sanctions) ? vd.sanctions : {};
  const hasSanctions = ["clean", "hit", "unavailable"].includes(sanc.status);

  const risk = isPlainObject(vd.risk) ? vd.risk : {};
  const aegrmField = isPlainObject(risk.aegrm_guarantees)
    ? risk.aegrm_guarantees
    : {};
  const aegrm = isPlainObject(aegrmField.value) ? aegrmField.value : undefined;
  const aegrmOk = Boolean(aegrm?.has_data);
  const hist = Array.isArray(vd.historical_flags) ? vd.historical_flags : [];
  const histOk = hist.length > 0;
  const hasGarantii = aegrmOk || histOk;

  const historicalFlags: HistoricalFlagNormalized[] = histOk
    ? hist.map((fl: unknown) => {
        if (isPlainObject(fl)) {
          // osint_client (backend/agents/tools/osint_client.py) emite
          // {type(slug), label(human), severity, snippet}. Preferinta
          // canonica: label peste type, snippet peste detail.
          return {
            isDict: true,
            label: String(
              fl.label ?? fl.type ?? fl.title ?? fl.category ?? "Semnal",
            ),
            detail: String(
              fl.snippet ?? fl.detail ?? fl.description ?? fl.text ?? "",
            ),
            date: String(fl.date ?? fl.data ?? ""),
            severity: String(fl.severity ?? "INFO").toUpperCase(),
          };
        }
        return {
          isDict: false,
          label: "",
          detail: String(fl),
          date: "",
          severity: "INFO",
        };
      })
    : [];

  const funding = isPlainObject(vd.funding_programs) ? vd.funding_programs : {};
  const hasFunding =
    Array.isArray(funding.eligible) && funding.eligible.length > 0;

  const cred = isPlainObject(vd.credit_exposure) ? vd.credit_exposure : {};
  const hasCred = "expunere_ron" in cred;

  return {
    predictiveScores: { shown: hasPred, data: pred },
    benchmark: { shown: hasBench, data: bench },
    eurostatSector: { shown: hasEust, data: eust },
    seap: { shown: hasSeap, data: seap },
    tenderOpportunities: { shown: hasOpp, data: opp },
    actionariat: { shown: hasActionariat, actOk, act, relFlags },
    sanctions: { shown: hasSanctions, data: sanc },
    garantii: {
      shown: hasGarantii,
      aegrmOk,
      aegrm,
      histOk,
      historicalFlags,
      rnpmUrl: RNPM_MANUAL_URL,
      rnpmManual: RNPM_MANUAL_MESSAGE,
    },
    fundingPrograms: { shown: hasFunding, data: funding },
    creditExposure: { shown: hasCred, data: cred },
  };
}
