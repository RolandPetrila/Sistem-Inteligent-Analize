from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


# --- Enums ---

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DONE = "DONE"
    FAILED = "FAILED"


class AnalysisType(str, Enum):
    FULL_COMPANY_PROFILE = "FULL_COMPANY_PROFILE"
    COMPETITION_ANALYSIS = "COMPETITION_ANALYSIS"
    PARTNER_RISK_ASSESSMENT = "PARTNER_RISK_ASSESSMENT"
    TENDER_OPPORTUNITIES = "TENDER_OPPORTUNITIES"
    FUNDING_OPPORTUNITIES = "FUNDING_OPPORTUNITIES"
    MARKET_ENTRY_ANALYSIS = "MARKET_ENTRY_ANALYSIS"
    LEAD_GENERATION = "LEAD_GENERATION"
    MONITORING_SETUP = "MONITORING_SETUP"
    CUSTOM_REPORT = "CUSTOM_REPORT"


class ReportLevel(int, Enum):
    RAPID = 1
    STANDARD = 2
    COMPLET = 3


class TrustLevel(str, Enum):
    OFICIAL = "OFICIAL"
    VERIFICAT = "VERIFICAT"
    ESTIMAT = "ESTIMAT"
    NECONCLUDENT = "NECONCLUDENT"
    INDISPONIBIL = "INDISPONIBIL"


class RiskScore(str, Enum):
    VERDE = "Verde"
    GALBEN = "Galben"
    ROSU = "Rosu"


# --- Analysis type metadata ---

ANALYSIS_TYPES_META = {
    AnalysisType.FULL_COMPANY_PROFILE: {
        "name": "Profil Complet Firma",
        "description": "Analiza exhaustiva a unei firme specifice - tot ce e disponibil public.",
        "icon": "Building2",
        "time_estimate": {1: "15-30 min", 2: "1-2 ore", 3: "2-4 ore"},
        "feasibility": 85,
        "questions": [
            {"id": "cui", "label": "CUI sau denumire firma", "type": "text", "required": True},
            {"id": "county", "label": "Judetul/localitatea sediului", "type": "text", "required": False},
            {"id": "purpose", "label": "Scopul analizei", "type": "select",
             "options": ["Due diligence", "Parteneriat", "Concurenta", "Altul"]},
            {"id": "focus", "label": "Aspecte prioritare de investigat", "type": "text", "required": False},
            {"id": "period", "label": "Perioada date financiare", "type": "select",
             "options": ["Ultimii 3 ani", "Ultimii 5 ani", "Alt interval"]},
        ],
    },
    AnalysisType.COMPETITION_ANALYSIS: {
        "name": "Analiza Competitie",
        "description": "Identifica si analizeaza competitorii directi dintr-un domeniu si zona.",
        "icon": "Swords",
        "time_estimate": {1: "30-60 min", 2: "1-2 ore", 3: "2-3 ore"},
        "feasibility": 70,
        "questions": [
            {"id": "cui", "label": "Firma client sau domeniul de activitate", "type": "text", "required": True},
            {"id": "area", "label": "Zona geografica de interes", "type": "select",
             "options": ["Judet", "Regiune", "National"]},
            {"id": "scope", "label": "Definitia competitorului", "type": "select",
             "options": ["Acelasi CAEN exact", "CAEN similar", "Intreaga industrie"]},
            {"id": "focus", "label": "Aspect principal al competitiei", "type": "select",
             "options": ["Preturi", "Servicii", "Dimensiune", "Prezenta online"]},
            {"id": "known_competitors", "label": "Firme deja cunoscute (optional)", "type": "text", "required": False},
        ],
    },
    AnalysisType.PARTNER_RISK_ASSESSMENT: {
        "name": "Evaluare Risc Partener",
        "description": "Verificare rapida inainte de contract sau parteneriat.",
        "icon": "ShieldCheck",
        "time_estimate": {1: "10-20 min", 2: "15-45 min", 3: "30-60 min"},
        "feasibility": 80,
        "questions": [
            {"id": "cui", "label": "CUI sau denumirea firmei", "type": "text", "required": True},
            {"id": "partnership_type", "label": "Tipul parteneriatului", "type": "select",
             "options": ["Furnizor", "Client", "Asociat", "Joint-venture"]},
            {"id": "contract_value", "label": "Valoarea estimata contract (RON)", "type": "text", "required": False},
            {"id": "concerns", "label": "Ingrijorari specifice", "type": "text", "required": False},
            {"id": "urgency", "label": "Termen decizie", "type": "select",
             "options": ["Urgent (sub 24h)", "Normal (2-3 zile)"]},
        ],
    },
    AnalysisType.TENDER_OPPORTUNITIES: {
        "name": "Oportunitati Licitatii & Contracte",
        "description": "Gaseste licitatii publice active si contracte castigabile.",
        "icon": "FileText",
        "time_estimate": {1: "15-30 min", 2: "30-60 min", 3: "1-2 ore"},
        "feasibility": 75,
        "questions": [
            {"id": "cui", "label": "CUI sau profilul firmei", "type": "text", "required": True},
            {"id": "services", "label": "Tipul de servicii/produse oferite", "type": "text", "required": True},
            {"id": "area", "label": "Zona geografica preferata", "type": "select",
             "options": ["Local", "Regional", "National"]},
            {"id": "value_range", "label": "Valoare contracte de interes (RON)", "type": "text", "required": False},
            {"id": "experience", "label": "Experienta cu licitatii publice", "type": "select",
             "options": ["Da", "Nu"]},
        ],
    },
    AnalysisType.FUNDING_OPPORTUNITIES: {
        "name": "Fonduri & Finantari Disponibile",
        "description": "Identifica programele de finantare europene si nationale aplicabile.",
        "icon": "Banknote",
        "time_estimate": {1: "20-40 min", 2: "45-90 min", 3: "1-2 ore"},
        "feasibility": 60,
        "questions": [
            {"id": "cui", "label": "CUI sau profilul firmei", "type": "text", "required": True},
            {"id": "investment_type", "label": "Tipul investitiei", "type": "select",
             "options": ["Echipamente", "Digitalizare", "Angajari", "Export", "Cercetare", "Altul"]},
            {"id": "amount", "label": "Suma necesara (RON)", "type": "text", "required": False},
            {"id": "debts", "label": "Firma are datorii la ANAF?", "type": "select", "options": ["Da", "Nu"]},
            {"id": "employees", "label": "Numar angajati", "type": "select",
             "options": ["Micro (<10)", "Mica (<50)", "Medie (<250)", "Mare (250+)"]},
            {"id": "region", "label": "Regiunea de dezvoltare", "type": "text", "required": True},
        ],
    },
    AnalysisType.MARKET_ENTRY_ANALYSIS: {
        "name": "Analiza Intrare pe Piata",
        "description": "Analiza completa pentru intrarea pe o piata noua.",
        "icon": "TrendingUp",
        "time_estimate": {1: "30-60 min", 2: "1-2 ore", 3: "2-4 ore"},
        "feasibility": 65,
        "questions": [
            {"id": "company", "label": "Descrierea afacerii (CUI daca exista)", "type": "text", "required": True},
            {"id": "target_market", "label": "Piata/domeniul tinta", "type": "text", "required": True},
            {"id": "area", "label": "Zona geografica", "type": "select",
             "options": ["Judet", "Regiune", "National"]},
            {"id": "advantage", "label": "Avantaj competitiv", "type": "select",
             "options": ["Pret", "Calitate", "Nisa", "Inovatie"]},
            {"id": "budget", "label": "Buget estimat intrare pe piata", "type": "text", "required": False},
        ],
    },
    AnalysisType.LEAD_GENERATION: {
        "name": "Prospectare Clienti Potentiali",
        "description": "Identifica firme care ar putea deveni clienti.",
        "icon": "Users",
        "time_estimate": {1: "20-40 min", 2: "1-2 ore", 3: "2-3 ore"},
        "feasibility": 55,
        "questions": [
            {"id": "company", "label": "Profilul firmei care cauta clienti", "type": "text", "required": True},
            {"id": "ideal_client", "label": "Profilul clientului ideal", "type": "text", "required": True},
            {"id": "priority", "label": "Criteriu de prioritizare", "type": "select",
             "options": ["Firme in crestere", "Firme cu licitatii active", "Firme cu probleme cunoscute"]},
            {"id": "count", "label": "Cate firme sa identifice", "type": "select",
             "options": ["10", "25", "50", "Cat gaseste"]},
        ],
    },
    AnalysisType.MONITORING_SETUP: {
        "name": "Monitorizare Periodica",
        "description": "Configureaza monitorizarea continua pentru o firma sau domeniu.",
        "icon": "Bell",
        "time_estimate": {1: "-", 2: "-", 3: "-"},
        "feasibility": 0,
        "questions": [],
        "deferred": True,
    },
    AnalysisType.CUSTOM_REPORT: {
        "name": "Raport Personalizat",
        "description": "Orice combinatie de sectiuni, cerere libera.",
        "icon": "Sparkles",
        "time_estimate": {1: "Variabil", 2: "Variabil", 3: "Variabil"},
        "feasibility": 70,
        "questions": [
            {"id": "description", "label": "Descrie ce vrei sa analizezi", "type": "textarea", "required": True},
        ],
    },
}


# --- Request/Response schemas ---

class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_type: AnalysisType
    report_level: int = Field(default=2, ge=1, le=3)
    input_params: dict = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    type: str
    status: JobStatus
    report_level: int
    input_data: dict | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    progress_percent: int = 0
    current_step: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class ReportResponse(BaseModel):
    id: str
    job_id: str
    company_id: str | None = None
    report_type: str
    report_level: int
    title: str | None = None
    summary: str | None = None
    risk_score: str | None = None
    created_at: str
    formats_available: list[str] = Field(default_factory=list)


class CompanyResponse(BaseModel):
    id: str
    cui: str | None = None
    name: str
    caen_code: str | None = None
    caen_description: str | None = None
    county: str | None = None
    city: str | None = None
    first_analyzed_at: str | None = None
    last_analyzed_at: str | None = None
    analysis_count: int = 0


class AnalysisTypeResponse(BaseModel):
    type: str
    name: str
    description: str
    icon: str
    time_estimate: dict
    feasibility: int
    questions: list[dict]
    deferred: bool = False


class StatsResponse(BaseModel):
    total_jobs: int = 0
    completed_jobs: int = 0
    total_reports: int = 0
    total_companies: int = 0
    jobs_this_month: int = 0


class WSProgressMessage(BaseModel):
    type: str  # progress | agent_complete | agent_warning | job_complete | job_failed
    job_id: str
    percent: int | None = None
    step: str | None = None
    eta_seconds: int | None = None
    agent: str | None = None
    status: str | None = None
    message: str | None = None
    report_id: str | None = None
    formats: list[str] | None = None
    error: str | None = None
    retry_available: bool | None = None
