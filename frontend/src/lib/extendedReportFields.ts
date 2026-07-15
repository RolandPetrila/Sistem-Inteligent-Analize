/**
 * Extrage campurile bogate din full_data care NU sunt acoperite de
 * backend/reports/rich_fields.py (acela mapeaza doar cele 10 grupuri deja
 * randate in HTML/PDF/DOCX). Astea existau in full_data la client dar nu
 * erau randate NICAIERI in frontend inainte de P0-2 (2026-07-15) — verificat
 * cu grep pe frontend/src (0 rezultate pentru oricare din cheile de mai jos).
 */

export interface DueDiligenceItem {
  name: string;
  status: string;
  severity: string;
  source: string;
}

export interface EarlyWarningItem {
  warning: string;
  confidence: number;
  severity: string;
}

export interface CompanyNetworkPerson {
  name: string;
  role?: string;
  ownership_pct?: number | null;
}

export interface CompanyNetworkRelatedCompany {
  cui: string;
  company_name: string;
  is_active?: number | null;
  depth?: number;
}

export interface CompanyNetworkRiskFlag {
  type: string;
  severity: string;
  detail: string;
}

export interface CompanyNetworkData {
  has_data?: boolean;
  persons?: CompanyNetworkPerson[];
  related_companies?: CompanyNetworkRelatedCompany[];
  risk_flags?: CompanyNetworkRiskFlag[];
  total_connected?: number;
  stats?: { active?: number; inactive?: number; unknown_status?: number };
}

function isPlainObject(v: unknown): v is Record<string, any> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

export function getDueDiligenceItems(
  fullData: Record<string, any> | null | undefined,
): DueDiligenceItem[] {
  const items = fullData?.due_diligence;
  return Array.isArray(items) ? items : [];
}

/**
 * Semnalele de avertizare timpurie vin din risk_score.early_warning_confidence
 * (populat de backend/agents/verification/scoring.py), NU din cheia top-level
 * `early_warnings` -- aceea exista in contractul de retur dar nu e scrisa
 * NICIODATA cu continut (confirmat prin inspectie DB reala pe 5 rapoarte
 * recente: mereu `[]`), acelasi tipar de "cod care citeste o cheie pe care
 * nimic nu o scrie" ca maps_rating/monitorul_oficial din Runda 1.
 * backend/reports/html_generator.py foloseste deja calea reala
 * (risk_score_obj.get("early_warning_confidence")) -- oglindita aici.
 */
export function getEarlyWarnings(
  fullData: Record<string, any> | null | undefined,
): EarlyWarningItem[] {
  const riskScore = fullData?.risk_score;
  const items = isPlainObject(riskScore)
    ? riskScore.early_warning_confidence
    : undefined;
  return Array.isArray(items) ? items : [];
}

/**
 * Reteaua de firme (persoane comune / firme conexe / risk flags) --
 * backend/agents/tools/network_client.py::get_company_network(). Gate pe
 * `has_data` + cel putin o persoana/firma conexa (identic cu conditia din
 * html_generator._build_company_network_html, dar folosind cheile reale
 * `persons`/`related_companies` -- html_generator insusi citeste
 * stats.total_persons/total_firms, chei pe care network_client NU le scrie
 * niciodata (scrie stats.active/inactive/unknown_status) -- adjacent finding,
 * semnalat separat, neatins aici).
 */
export function getCompanyNetwork(
  fullData: Record<string, any> | null | undefined,
): CompanyNetworkData | null {
  const net = fullData?.company_network;
  if (!isPlainObject(net) || !net.has_data) return null;
  const hasPersons = Array.isArray(net.persons) && net.persons.length > 0;
  const hasRelated =
    Array.isArray(net.related_companies) && net.related_companies.length > 0;
  if (!hasPersons && !hasRelated) return null;
  return net as CompanyNetworkData;
}

export function getKeyTakeaways(
  fullData: Record<string, any> | null | undefined,
): string | null {
  const kt = fullData?.key_takeaways;
  return typeof kt === "string" && kt.trim().length > 0 ? kt : null;
}

export interface MapsRating {
  found?: boolean;
  name?: string;
  rating?: number;
  reviews_count?: number;
  address?: string;
}

export interface FreshnessEntry {
  data_age_years?: number;
  fresh?: boolean;
  latest_year?: number;
  note?: string;
}

export interface WebIntelSignals {
  mapsRating: MapsRating | null;
  freshness: Record<string, FreshnessEntry> | null;
}

/**
 * Semnale orfane cablate in P0-1 (2026-07-12, official_data -> verified) dar
 * inca nerandate in frontend: maps_rating (Google Maps) + data_freshness
 * (varsta datelor per sursa).
 */
export function getWebIntelSignals(
  fullData: Record<string, any> | null | undefined,
): WebIntelSignals {
  const maps = fullData?.maps_rating;
  const mapsRating =
    isPlainObject(maps) && maps.found ? (maps as MapsRating) : null;
  const freshness = fullData?.data_freshness;
  return {
    mapsRating,
    freshness:
      isPlainObject(freshness) && Object.keys(freshness).length > 0
        ? (freshness as Record<string, FreshnessEntry>)
        : null,
  };
}
