import type { RiskScore } from "./types";

/**
 * Sursa unica a pragului scor->eticheta (DRY #2, 2026-07-14). Oglinda TypeScript a
 * backend/agents/verification/scoring.py::risk_bucket() (backed de COLOR_MAP) —
 * pragurile trebuie sa ramana identice in ambele limbaje; schimba-le in AMBELE
 * fisiere daca se schimba vreodata, niciodata doar unul.
 */
export function getRiskBucket(score: number): RiskScore {
  if (score >= 70) return "Verde";
  if (score >= 40) return "Galben";
  return "Rosu";
}
