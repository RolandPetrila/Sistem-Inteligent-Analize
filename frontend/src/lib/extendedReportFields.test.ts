import { describe, it, expect } from "vitest";
import {
  getDueDiligenceItems,
  getEarlyWarnings,
  getCompanyNetwork,
  getKeyTakeaways,
  getWebIntelSignals,
} from "./extendedReportFields";

describe("getDueDiligenceItems", () => {
  it("returneaza lista cand exista", () => {
    const items = getDueDiligenceItems({
      due_diligence: [
        {
          name: "Firma activa",
          status: "DA",
          severity: "info",
          source: "ANAF",
        },
      ],
    });
    expect(items).toHaveLength(1);
  });

  it("returneaza [] cand lipseste sau nu e array", () => {
    expect(getDueDiligenceItems({})).toEqual([]);
    expect(getDueDiligenceItems(null)).toEqual([]);
    expect(getDueDiligenceItems({ due_diligence: "not-an-array" })).toEqual([]);
  });
});

describe("getEarlyWarnings", () => {
  it("citeste risk_score.early_warning_confidence, NU cheia orfana top-level early_warnings", () => {
    const fullData = {
      // Cheie orfana -- exista in contract dar backend-ul nu scrie niciodata
      // continut in ea (confirmat: mereu [] pe 5 rapoarte reale din DB).
      early_warnings: [],
      risk_score: {
        early_warning_confidence: [
          {
            warning: "Risc fiscal: stare TRANSFER",
            confidence: 90,
            severity: "HIGH",
          },
        ],
      },
    };
    const result = getEarlyWarnings(fullData);
    expect(result).toHaveLength(1);
    expect(result[0].warning).toContain("Risc fiscal");
  });

  it("returneaza [] cand risk_score sau early_warning_confidence lipsesc", () => {
    expect(getEarlyWarnings({})).toEqual([]);
    expect(getEarlyWarnings({ risk_score: {} })).toEqual([]);
    expect(
      getEarlyWarnings({ early_warnings: [{ warning: "orfan" }] }),
    ).toEqual([]);
  });
});

describe("getCompanyNetwork", () => {
  it("returneaza null cand has_data e false (cazul comun -- fara administratori in DB)", () => {
    expect(
      getCompanyNetwork({
        company_network: {
          has_data: false,
          persons: [],
          related_companies: [],
        },
      }),
    ).toBeNull();
  });

  it("returneaza null cand has_data e true dar listele sunt goale", () => {
    expect(
      getCompanyNetwork({
        company_network: { has_data: true, persons: [], related_companies: [] },
      }),
    ).toBeNull();
  });

  it("returneaza reteaua cand has_data + cel putin o persoana/firma", () => {
    const net = getCompanyNetwork({
      company_network: {
        has_data: true,
        persons: [{ name: "Persoana X", role: "administrator" }],
        related_companies: [],
        risk_flags: [],
        total_connected: 0,
      },
    });
    expect(net).not.toBeNull();
    expect(net!.persons).toHaveLength(1);
  });
});

describe("getKeyTakeaways", () => {
  it("returneaza textul cand e string nevid", () => {
    expect(getKeyTakeaways({ key_takeaways: "• Punct cheie" })).toBe(
      "• Punct cheie",
    );
  });

  it("returneaza null pentru string gol/whitespace sau tip gresit", () => {
    expect(getKeyTakeaways({ key_takeaways: "   " })).toBeNull();
    expect(getKeyTakeaways({ key_takeaways: null })).toBeNull();
    expect(getKeyTakeaways({})).toBeNull();
  });
});

describe("getWebIntelSignals", () => {
  it("mapsRating: shown doar cand found e true", () => {
    expect(
      getWebIntelSignals({
        maps_rating: { found: true, name: "X", rating: 4.5 },
      }).mapsRating,
    ).not.toBeNull();
    expect(
      getWebIntelSignals({ maps_rating: { found: false } }).mapsRating,
    ).toBeNull();
    expect(getWebIntelSignals({}).mapsRating).toBeNull();
  });

  it("freshness: shown doar cand exista chei", () => {
    expect(
      getWebIntelSignals({ data_freshness: { anaf_bilant: { fresh: true } } })
        .freshness,
    ).not.toBeNull();
    expect(getWebIntelSignals({ data_freshness: {} }).freshness).toBeNull();
    expect(getWebIntelSignals({}).freshness).toBeNull();
  });
});
