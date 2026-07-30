/**
 * CERINTA #18 (P6-live): oglinda TS a `backend/reports/section_visibility.py`.
 *
 * Sinteza marcheaza fillerul "date insuficiente" cu `insufficient_data_filler=True` la un
 * PUNCT UNIC de emisie (`agent_synthesis.generate_section`). Raportele de pe disc
 * (HTML/PDF/DOCX/PPTX) omit deja aceste sectiuni via `visible_sections`. Aici facem ACEEASI
 * omitere pe vizualizarea LIVE din `ReportView`, ca livrabilul descarcat si vederea din PWA sa
 * NU se contrazica pe aceeasi sectiune.
 *
 * Reguli (identice cu backend-ul):
 * - cheiaza omiterea pe MARKER, NU pe `word_count===0` (o sectiune scurta legitima l-ar avea) si
 *   NU pe substring-matching pe proza (o editare a textului ar dezactiva tacut omiterea);
 * - never-empty (invariant #4): daca TOATE sectiunile sunt filler, le pastreaza pe toate —
 *   atunci fillerul ESTE raspunsul onest (ex. COMPETITION_ANALYSIS cu competitie insuficienta).
 */

// Acelasi string ca backend `section_visibility.py::INSUFFICIENT_DATA_MARKER`. Daca backend-ul il
// redenumeste, testul (care afirma valoarea literala) pica zgomotos.
export const INSUFFICIENT_DATA_MARKER = "insufficient_data_filler";

/**
 * True daca `value` e fillerul determinist "date insuficiente" (marcat la emisie).
 *
 * Garda pt non-obiect e portanta, nu decorativa: pe calea de eroare a orchestratorului o sectiune
 * poate fi un STRING (nu un dict) — string/null/undefined -> ne-filler.
 */
export function isFillerSection(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as Record<string, unknown>)[INSUFFICIENT_DATA_MARKER] === true
  );
}

/**
 * Imparte intrarile `[key, section]` in `visible` (de randat in lista narativa) si `hidden`
 * (fillerele "date insuficiente", afisate degajat sub lista). UN SINGUR loc care tine invariantul
 * never-empty: daca dupa filtrare NU ar ramane nicio sectiune vizibila, pastreaza TOTUL vizibil si
 * nu ascunde nimic (fillerul e atunci raspunsul onest, nu zgomot de omis).
 */
export function partitionSections<T>(entries: [string, T][]): {
  visible: [string, T][];
  hidden: [string, T][];
} {
  const nonFiller = entries.filter(([, v]) => !isFillerSection(v));
  if (nonFiller.length === 0) {
    return { visible: entries, hidden: [] };
  }
  const filler = entries.filter(([, v]) => isFillerSection(v));
  return { visible: nonFiller, hidden: filler };
}

/** Sectiunile de randat in lista narativa, in ordinea originala (fara fillere), cu never-empty. */
export function visibleSections<T>(entries: [string, T][]): [string, T][] {
  return partitionSections(entries).visible;
}
