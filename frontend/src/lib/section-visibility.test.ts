/**
 * CERINTA #18 (P6-live) — non-vacuitate pentru omiterea sectiunilor filler in ReportView.
 *
 * Helper-ul NU exista pe HEAD (cod vechi) -> importul de mai jos e nerezolvabil -> suita pica
 * structural pe cod vechi. Pe cod nou, testeaza: fillerul (marcat) e EXCLUS din `visibleSections`,
 * o sectiune reala e PASTRATA, toate-filler -> pastrate (never-empty), string/null/undefined ->
 * tratate ca ne-filler (calea de eroare orchestrator poate stoca un string, nu un dict).
 */
import { describe, it, expect } from "vitest";
import {
  INSUFFICIENT_DATA_MARKER,
  isFillerSection,
  partitionSections,
  visibleSections,
} from "./section-visibility";

// Forma REALA a fillerului, verificata pe payload-ul viu GET /api/reports/{id}
// (report `fd0ce818-…`, job `5a432e0e`, MOSSLEIN): competition = dict cu title/content/
// word_count=0 + insufficient_data_filler=True.
const FILLER = {
  title: "Analiza Competitie",
  content:
    "Sectiunea 'Analiza Competitie' nu a putut fi generata din cauza datelor insuficiente...",
  word_count: 0,
  insufficient_data_filler: true,
};
const REAL = {
  title: "Rezumat Executiv",
  content: "Firma X are...",
  word_count: 320,
};
// O sectiune scurta legitima (word_count 0) FARA marker NU trebuie tratata ca filler.
const SHORT_REAL = { title: "Nota", content: "", word_count: 0 };

describe("section-visibility", () => {
  it("markerul TS oglindeste EXACT backend-ul (redenumire backend => test rosu)", () => {
    expect(INSUFFICIENT_DATA_MARKER).toBe("insufficient_data_filler");
  });

  describe("isFillerSection", () => {
    it("dict marcat -> true", () => {
      expect(isFillerSection(FILLER)).toBe(true);
    });
    it("dict real (fara marker) -> false", () => {
      expect(isFillerSection(REAL)).toBe(false);
    });
    it("marker false explicit -> false", () => {
      expect(
        isFillerSection({ ...REAL, insufficient_data_filler: false }),
      ).toBe(false);
    });
    it("word_count===0 FARA marker -> false (nu cheiem pe word_count)", () => {
      expect(isFillerSection(SHORT_REAL)).toBe(false);
    });
    it("string / null / undefined -> false (calea de eroare orchestrator)", () => {
      expect(isFillerSection("un text brut")).toBe(false);
      expect(isFillerSection(null)).toBe(false);
      expect(isFillerSection(undefined)).toBe(false);
    });
  });

  describe("visibleSections / partitionSections", () => {
    it("exclude fillerul, pastreaza sectiunile reale, in ordine", () => {
      const entries: [string, unknown][] = [
        ["executive_summary", REAL],
        ["competition", FILLER],
        ["recommendations", REAL],
      ];
      const visible = visibleSections(entries).map(([k]) => k);
      expect(visible).toEqual(["executive_summary", "recommendations"]);
      const { hidden } = partitionSections(entries);
      expect(hidden.map(([k]) => k)).toEqual(["competition"]);
    });

    it("never-empty: TOATE filler -> pastrate vizibile, nimic ascuns", () => {
      const entries: [string, unknown][] = [
        ["competition", FILLER],
        ["market_position", { ...FILLER, title: "Pozitie" }],
      ];
      const { visible, hidden } = partitionSections(entries);
      expect(visible.map(([k]) => k)).toEqual([
        "competition",
        "market_position",
      ]);
      expect(hidden).toEqual([]);
    });

    it("niciun filler -> toate vizibile, hidden gol", () => {
      const entries: [string, unknown][] = [
        ["executive_summary", REAL],
        ["nota", SHORT_REAL],
      ];
      const { visible, hidden } = partitionSections(entries);
      expect(visible.map(([k]) => k)).toEqual(["executive_summary", "nota"]);
      expect(hidden).toEqual([]);
    });

    it("intrari goale -> gol (fara crash)", () => {
      const { visible, hidden } = partitionSections([]);
      expect(visible).toEqual([]);
      expect(hidden).toEqual([]);
    });
  });
});
