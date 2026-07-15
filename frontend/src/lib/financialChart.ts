export interface FinancialChartData {
  years: string[];
  ca: (number | null)[];
  profit: (number | null)[];
  angajati: (number | null)[];
}

interface TrendMetricValue {
  year: number | string;
  value: number;
}

interface TrendMetric {
  values?: TrendMetricValue[];
}

interface TrendFinanciar {
  cifra_afaceri_neta?: TrendMetric;
  profit_net?: TrendMetric;
  numar_mediu_salariati?: TrendMetric;
}

function toSeries(metric: TrendMetric | undefined): Map<string, number> {
  const map = new Map<string, number>();
  for (const v of metric?.values ?? []) {
    if (v && v.year != null && typeof v.value === "number") {
      map.set(String(v.year), v.value);
    }
  }
  return map;
}

/**
 * Extrage seria multi-an pentru tab-ul "Grafice" din
 * financial.trend_financiar.value (populat de ANAF Bilant multi-an —
 * backend/agents/tools/anaf_bilant_client.py::_calculate_trends, expus
 * prin backend/agents/agent_verification.py ca financial.trend_financiar).
 *
 * NU financial.cifra_afaceri.historical / financial.profit_net.historical /
 * financial.numar_angajati.historical -- niciuna din aceste chei "historical"
 * nu e scrisa VREODATA de backend (verificat cu grep pe tot backend/ +
 * inspectie DB reala, 2026-07-15 P0-3). Acelea produceau mereu `{}` -> tab
 * mort pentru orice firma, indiferent cate date financiare existau real.
 *
 * Forma reala confirmata din data/ris.db (financial.trend_financiar.value):
 *   { cifra_afaceri_neta: { values: [{year, value}, ...], ... },
 *     profit_net: { values: [...] },
 *     numar_mediu_salariati: { values: [...] },
 *     capitaluri_proprii: { values: [...] } }
 */
export function buildFinancialChartData(
  financial: Record<string, unknown> | null | undefined,
): FinancialChartData | null {
  if (!financial) return null;
  const trendField = financial.trend_financiar as
    { value?: TrendFinanciar } | undefined;
  const trend = trendField?.value;
  if (!trend || typeof trend !== "object") return null;

  const caSeries = toSeries(trend.cifra_afaceri_neta);
  const profitSeries = toSeries(trend.profit_net);
  const angajatiSeries = toSeries(trend.numar_mediu_salariati);

  const years = [...new Set([...caSeries.keys(), ...profitSeries.keys()])]
    .sort()
    .slice(-5);
  if (years.length < 2) return null;

  return {
    years,
    ca: years.map((y) => caSeries.get(y) ?? null),
    profit: years.map((y) => profitSeries.get(y) ?? null),
    angajati: years.map((y) => angajatiSeries.get(y) ?? null),
  };
}
