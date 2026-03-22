export const ANALYSIS_TYPE_LABELS: Record<string, string> = {
  FULL_COMPANY_PROFILE: "Profil Complet Firma",
  COMPETITION_ANALYSIS: "Analiza Competitie",
  PARTNER_RISK_ASSESSMENT: "Evaluare Risc Partener",
  TENDER_OPPORTUNITIES: "Oportunitati Licitatii",
  FUNDING_OPPORTUNITIES: "Fonduri & Finantari",
  MARKET_ENTRY_ANALYSIS: "Analiza Intrare Piata",
  LEAD_GENERATION: "Prospectare Clienti",
  MONITORING_SETUP: "Monitorizare Periodica",
  CUSTOM_REPORT: "Raport Personalizat",
};

export const JOB_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  PENDING: { label: "In asteptare", color: "text-gray-400" },
  RUNNING: { label: "In executie", color: "text-accent-secondary" },
  PAUSED: { label: "Pauza", color: "text-yellow-400" },
  DONE: { label: "Finalizat", color: "text-green-400" },
  FAILED: { label: "Esuat", color: "text-red-400" },
};

export const TRUST_LEVEL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  OFICIAL: { label: "Oficial", color: "text-trust-oficial", bg: "bg-trust-oficial/10" },
  VERIFICAT: { label: "Verificat", color: "text-trust-verificat", bg: "bg-trust-verificat/10" },
  ESTIMAT: { label: "Estimat", color: "text-trust-estimat", bg: "bg-trust-estimat/10" },
  NECONCLUDENT: { label: "Neconcludent", color: "text-trust-neconcludent", bg: "bg-trust-neconcludent/10" },
  INDISPONIBIL: { label: "Indisponibil", color: "text-trust-indisponibil", bg: "bg-trust-indisponibil/10" },
};

export const REPORT_LEVEL_LABELS: Record<number, { name: string; description: string }> = {
  1: { name: "Rapid", description: "Doar surse oficiale, 10-30 min" },
  2: { name: "Standard", description: "Surse oficiale + web, 30-120 min" },
  3: { name: "Complet", description: "Toate sursele, 1-4 ore" },
};
