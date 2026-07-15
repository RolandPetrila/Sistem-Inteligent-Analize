import { describe, it, expect } from "vitest";
import { buildFinancialChartData } from "./financialChart";

// P0-3 (2026-07-15): tab-ul "Grafice" din ReportView era mort pentru orice
// firma -- codul vechi citea financial.cifra_afaceri.historical /
// financial.profit_net.historical / financial.numar_angajati.historical,
// chei pe care backend-ul nu le scrie NICIODATA. Forma reala confirmata
// dintr-un raport real din data/ris.db (anonimizat -- valorile numerice
// sunt reale, denumirea firmei NU e inclusa aici):
//   financial.trend_financiar.value.{cifra_afaceri_neta,profit_net,
//   numar_mediu_salariati}.values = [{year, value}, ...]
// (backend/agents/tools/anaf_bilant_client.py::_calculate_trends)
const REAL_TREND_FIXTURE = {
  trend_financiar: {
    value: {
      cifra_afaceri_neta: {
        name: "CA",
        values: [
          { year: 2019, value: 5589865 },
          { year: 2020, value: 5016203 },
          { year: 2021, value: 6309435 },
          { year: 2022, value: 9871200 },
          { year: 2023, value: 14150500 },
        ],
        growth_percent: 153.2,
        direction: "crestere",
      },
      profit_net: {
        name: "Profit Net",
        values: [
          { year: 2019, value: 615332 },
          { year: 2020, value: 671730 },
          { year: 2021, value: 328583 },
          { year: 2022, value: 980100 },
          { year: 2023, value: 1450900 },
        ],
        growth_percent: 135.9,
        direction: "crestere",
      },
      numar_mediu_salariati: {
        name: "Angajati",
        values: [
          { year: 2019, value: 11 },
          { year: 2020, value: 12 },
          { year: 2021, value: 12 },
          { year: 2022, value: 15 },
          { year: 2023, value: 23 },
        ],
        growth_percent: 109.1,
        direction: "crestere",
      },
      capitaluri_proprii: {
        name: "Capitaluri",
        values: [{ year: 2019, value: 1968509 }],
      },
    },
    trust: "OFICIAL",
    source: "ANAF",
  },
  cifra_afaceri: { value: 14150500 },
  profit_net: { value: 1450900 },
  numar_angajati: { value: 23 },
};

describe("buildFinancialChartData", () => {
  it("extrage 5 ani de date reale din financial.trend_financiar.value (fixture din DB reala anonimizata)", () => {
    const result = buildFinancialChartData(REAL_TREND_FIXTURE);
    expect(result).not.toBeNull();
    expect(result!.years).toEqual(["2019", "2020", "2021", "2022", "2023"]);
    expect(result!.ca).toEqual([5589865, 5016203, 6309435, 9871200, 14150500]);
    expect(result!.profit).toEqual([615332, 671730, 328583, 980100, 1450900]);
    expect(result!.angajati).toEqual([11, 12, 12, 15, 23]);
  });

  it("returneaza null cand financial e absent", () => {
    expect(buildFinancialChartData(null)).toBeNull();
    expect(buildFinancialChartData(undefined)).toBeNull();
  });

  it("returneaza null cand trend_financiar lipseste (firma fara bilant multi-an)", () => {
    expect(
      buildFinancialChartData({ cifra_afaceri: { value: 100 } }),
    ).toBeNull();
  });

  it("returneaza null cand exista un singur an de date (sub minimul de 2)", () => {
    const oneYear = {
      trend_financiar: {
        value: {
          cifra_afaceri_neta: { values: [{ year: 2023, value: 100 }] },
        },
      },
    };
    expect(buildFinancialChartData(oneYear)).toBeNull();
  });

  it("NU citeste cheile vechi *.historical -- regresie pentru bug-ul P0-3", () => {
    // Forma pe care codul VECHI o citea (financial.cifra_afaceri.historical) --
    // niciodata scrisa de backend. Cu date DOAR in aceasta forma, rezultatul
    // trebuie sa fie tot null (dovedeste ca noul cod nu "reinventeaza" acelasi bug).
    const onlyOldShape = {
      cifra_afaceri: { value: 100, historical: { "2022": 90, "2023": 100 } },
      profit_net: { value: 10, historical: { "2022": 8, "2023": 10 } },
    };
    expect(buildFinancialChartData(onlyOldShape)).toBeNull();
  });

  it("limiteaza la ultimii 5 ani cand exista mai multi", () => {
    const values = Array.from({ length: 8 }, (_, i) => ({
      year: 2016 + i,
      value: (i + 1) * 1000,
    }));
    const fin = {
      trend_financiar: {
        value: {
          cifra_afaceri_neta: { values },
          profit_net: { values },
        },
      },
    };
    const result = buildFinancialChartData(fin);
    expect(result!.years).toEqual(["2019", "2020", "2021", "2022", "2023"]);
  });
});
