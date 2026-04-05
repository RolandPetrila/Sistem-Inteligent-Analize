export type JobStatus = "PENDING" | "RUNNING" | "PAUSED" | "DONE" | "FAILED";

export type AnalysisType =
  | "FULL_COMPANY_PROFILE"
  | "COMPETITION_ANALYSIS"
  | "PARTNER_RISK_ASSESSMENT"
  | "TENDER_OPPORTUNITIES"
  | "FUNDING_OPPORTUNITIES"
  | "MARKET_ENTRY_ANALYSIS"
  | "LEAD_GENERATION"
  | "MONITORING_SETUP"
  | "CUSTOM_REPORT";

export type TrustLevel =
  | "OFICIAL"
  | "VERIFICAT"
  | "ESTIMAT"
  | "NECONCLUDENT"
  | "INDISPONIBIL";

export type RiskScore = "Verde" | "Galben" | "Rosu";

export interface Job {
  id: string;
  type: AnalysisType;
  status: JobStatus;
  report_level: number;
  input_data: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  progress_percent: number;
  current_step: string | null;
}

export interface Report {
  id: string;
  job_id: string;
  company_id: string | null;
  report_type: string;
  report_level: number;
  title: string | null;
  summary: string | null;
  risk_score: RiskScore | null;
  created_at: string;
  formats_available: string[];
}

export interface Company {
  id: string;
  cui: string | null;
  name: string;
  caen_code: string | null;
  caen_description: string | null;
  county: string | null;
  city: string | null;
  first_analyzed_at: string | null;
  last_analyzed_at: string | null;
  analysis_count: number;
  is_favorite?: number | boolean;
}

export interface AnalysisTypeInfo {
  type: AnalysisType;
  name: string;
  description: string;
  icon: string;
  time_estimate: Record<number, string>;
  feasibility: number;
  questions: QuestionDef[];
  deferred?: boolean;
}

export interface QuestionDef {
  id: string;
  label: string;
  type: "text" | "textarea" | "select";
  required?: boolean;
  options?: string[];
}

export interface Stats {
  total_jobs: number;
  completed_jobs: number;
  total_reports: number;
  total_companies: number;
  jobs_this_month: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  severity: "info" | "warning" | "error" | "success";
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface RiskMover {
  id: string;
  name: string;
  cui: string | null;
  current_score: number;
  previous_score: number;
  delta: number;
}

export interface TimelineEvent {
  type: "report" | "score_change" | "alert";
  title: string;
  detail: string | null;
  date: string;
  icon?: string;
}

export interface ReportDelta {
  has_delta: boolean;
  message?: string;
  previous_report_id?: string;
  previous_score?: number;
  current_score?: number;
  score_delta?: number;
  changes?: Array<{
    field: string;
    old: string | number | null;
    new: string | number | null;
  }>;
}

export interface ScoreTrendPoint {
  created_at: string;
  score: number;
  delta?: number;
}

export interface ScoringReason {
  text: string;
  impact: number;
}

export interface ScoringDimension {
  score: number;
  weight: number;
  reasons?: ScoringReason[];
  confidence?: number;
  raw_score?: number;
  insufficient_data?: boolean;
  data_available?: boolean;
}

export interface WSMessage {
  type:
    | "progress"
    | "agent_complete"
    | "agent_warning"
    | "job_complete"
    | "job_failed"
    | "pong";
  job_id?: string;
  percent?: number;
  step?: string;
  status?: string;
  eta_seconds?: number;
  agent?: string;
  message?: string;
  report_id?: string;
  formats?: string[];
  error?: string;
  retry_available?: boolean;
}
