import { describe, it, expect } from "vitest";
import { buildRichFieldsModel } from "./richFields";

// Oglinda TS a tests/test_rich_fields.py (backend). Fixture-uri sintetice
// (NU date reale de firme) -- gate-urile trebuie sa se comporte identic cu
// backend/reports/rich_fields.py::build_rich_fields_model.
describe("buildRichFieldsModel", () => {
  it("nu arata nimic pentru verified gol", () => {
    const model = buildRichFieldsModel({});
    expect(model.predictiveScores.shown).toBe(false);
    expect(model.benchmark.shown).toBe(false);
    expect(model.eurostatSector.shown).toBe(false);
    expect(model.seap.shown).toBe(false);
    expect(model.tenderOpportunities.shown).toBe(false);
    expect(model.actionariat.shown).toBe(false);
    expect(model.sanctions.shown).toBe(false);
    expect(model.garantii.shown).toBe(false);
    expect(model.fundingPrograms.shown).toBe(false);
    expect(model.creditExposure.shown).toBe(false);
  });

  it("nu arunca pentru null/undefined", () => {
    expect(() => buildRichFieldsModel(null)).not.toThrow();
    expect(() => buildRichFieldsModel(undefined)).not.toThrow();
  });

  it("predictive_scores: gate pe summary prezent", () => {
    expect(
      buildRichFieldsModel({ predictive_scores: { summary: "OK" } })
        .predictiveScores.shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ predictive_scores: {} }).predictiveScores.shown,
    ).toBe(false);
  });

  it("benchmark: gate pe available + comparisons", () => {
    expect(
      buildRichFieldsModel({
        benchmark: { available: true, comparisons: [{ metric: "CA" }] },
      }).benchmark.shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ benchmark: { available: true, comparisons: [] } })
        .benchmark.shown,
    ).toBe(false);
  });

  it("seap: unwrap .value + gate pe total_contracts > 0", () => {
    const model = buildRichFieldsModel({
      market: { seap: { value: { total_contracts: 3, contracts: [] } } },
    });
    expect(model.seap.shown).toBe(true);
    expect(model.seap.data.total_contracts).toBe(3);

    expect(
      buildRichFieldsModel({
        market: { seap: { value: { total_contracts: 0 } } },
      }).seap.shown,
    ).toBe(false);
  });

  it("actionariat: shown daca act.available SAU relations.flags nevid", () => {
    expect(
      buildRichFieldsModel({ actionariat: { available: true } }).actionariat
        .shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ relations: { flags: [{ type: "X" }] } })
        .actionariat.shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ actionariat: { available: false } }).actionariat
        .shown,
    ).toBe(false);
  });

  it("sanctions: shown pentru status clean/hit/unavailable, nu si altele", () => {
    for (const status of ["clean", "hit", "unavailable"]) {
      expect(
        buildRichFieldsModel({ sanctions: { status } }).sanctions.shown,
      ).toBe(true);
    }
    expect(
      buildRichFieldsModel({ sanctions: { status: "pending" } }).sanctions
        .shown,
    ).toBe(false);
  });

  it("garantii: unwrap risk.aegrm_guarantees.value + gate pe has_data SAU historical_flags", () => {
    const aegrmOnly = buildRichFieldsModel({
      risk: { aegrm_guarantees: { value: { has_data: true, count: 2 } } },
    });
    expect(aegrmOnly.garantii.shown).toBe(true);
    expect(aegrmOnly.garantii.aegrmOk).toBe(true);

    const histOnly = buildRichFieldsModel({
      historical_flags: [{ type: "cesiune_parti_sociale" }],
    });
    expect(histOnly.garantii.shown).toBe(true);
    expect(histOnly.garantii.aegrmOk).toBe(false);

    expect(buildRichFieldsModel({ historical_flags: [] }).garantii.shown).toBe(
      false,
    );
  });

  it("historical_flags: prefera label peste type si snippet peste detail (bug-ul din 2026-06-27)", () => {
    const model = buildRichFieldsModel({
      historical_flags: [
        {
          type: "cesiune_parti_sociale",
          label: "Cesiune parti sociale",
          snippet: "Descriere umana a evenimentului",
          severity: "medium",
          date: "2026-01-01",
        },
      ],
    });
    const flag = model.garantii.historicalFlags[0];
    expect(flag.label).toBe("Cesiune parti sociale");
    expect(flag.detail).toBe("Descriere umana a evenimentului");
    expect(flag.severity).toBe("MEDIUM");
  });

  it("historical_flags: fallback pe type/detail cand label/snippet lipsesc", () => {
    const model = buildRichFieldsModel({
      historical_flags: [{ type: "radiere", detail: "text vechi" }],
    });
    const flag = model.garantii.historicalFlags[0];
    expect(flag.label).toBe("radiere");
    expect(flag.detail).toBe("text vechi");
  });

  it("funding_programs: gate pe eligible nevid", () => {
    expect(
      buildRichFieldsModel({ funding_programs: { eligible: [{ nume: "X" }] } })
        .fundingPrograms.shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ funding_programs: { eligible: [] } })
        .fundingPrograms.shown,
    ).toBe(false);
  });

  it("credit_exposure: gate pe prezenta cheii expunere_ron", () => {
    expect(
      buildRichFieldsModel({ credit_exposure: { expunere_ron: 0 } })
        .creditExposure.shown,
    ).toBe(true);
    expect(
      buildRichFieldsModel({ credit_exposure: {} }).creditExposure.shown,
    ).toBe(false);
  });
});
