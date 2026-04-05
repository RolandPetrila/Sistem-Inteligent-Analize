# RECOMANDARI IMBUNATATIRI & COMPLETARI — RIS
**Data:** 2026-03-31 | **Versiune:** 1.0 | **Mod:** complet
**Proiect:** Roland Intelligence System (RIS) — Business Intelligence pentru firme romanesti
**Stack:** Python 3.13 + FastAPI + SQLite | React 19 + Vite + TypeScript + Tailwind CSS
**Stare curenta:** 17 faze complete, 182 teste, audit 90/100, 37 REST endpoints + 12 pagini

---

## PARTEA I — IMBUNATATIRI FUNCTII EXISTENTE

---

### 1. `calculate_risk_score()` — Corectare ponderare cu confidence

**Fisier:** `backend/agents/verification/scoring.py` — linia ~523
**Problema actuala:** Confidence weighting trage toate dimensiunile spre valoarea neutra 50. O dimensiune cu scor real 85 si confidence 0.3 devine ~60 — subestimand riscul real. Formula liniara `score * conf + 50 * (1-conf)` produce rezultate mediocre indiferent de datele reale.

**Imbunatatire propusa:**
- Inlocuire formula liniara cu power-law weighting care pastreaza directia scorului
- Dimensiuni cu confidence < 0.2 sa fie marcate "INSUFICIENT" in loc de mediate la 50
- Adaugare flag `low_confidence_dimensions` in output pentru transparenta

**Exemplu implementare:**
```python
# scoring.py — inlocuire bloc confidence weighting (~linia 523)
def _apply_confidence(raw_score: float, confidence: float) -> tuple[float, bool]:
    """Apply confidence weighting preserving score direction."""
    if confidence < 0.2:
        return raw_score, True  # insufficient data flag
    # Power-law: scorul se apropie de neutru proportional cu (1-conf)^2
    # dar pastreaza directia (sub/peste 50)
    neutral = 50.0
    distance = raw_score - neutral
    adjusted = neutral + distance * (confidence ** 0.5)
    return round(adjusted, 1), False

# In calculate_risk_score():
for dim_name, dim_data in dimensions.items():
    raw = dim_data["raw_score"]
    conf = dim_data.get("confidence", 1.0)
    adjusted, insufficient = _apply_confidence(raw, conf)
    dim_data["adjusted_score"] = adjusted
    dim_data["insufficient_data"] = insufficient
    if insufficient:
        low_conf_dims.append(dim_name)
```

**Complexitate:** Mica | **Impact:** Maxim — scorurile de risc sunt produsul principal al sistemului

---

### 2. `execute()` in OfficialAgent — Completeness score cu denominator dinamic

**Fisier:** `backend/agents/agent_official.py` — linia ~362
**Problema actuala:** Completeness score foloseste `max(5, 1)` ca denominator — arbitrar. Daca un tip de analiza necesita doar 3 surse (ex: COMPETITION_ANALYSIS), completeness de 60% e raportat gresit ca 100% (3/5 surse nu se numara ca lipsa).

**Imbunatatire propusa:**
- Denominator calculat dinamic pe baza surselor RELEVANTE pentru tipul de analiza
- Surse optionale (BPI, SEAP) sa nu penalizeze completeness daca analiza nu le necesita
- Completeness sa includa si calitatea datelor, nu doar prezenta (sursa cu 2 campuri vs 20)

**Exemplu implementare:**
```python
# agent_official.py — inlocuire bloc completeness (~linia 336-370)
REQUIRED_SOURCES_BY_TYPE = {
    "FULL_COMPANY_PROFILE": ["ANAF", "ANAF Bilant", "BNR", "openapi.ro", "BPI"],
    "COMPETITION_ANALYSIS": ["ANAF", "ANAF Bilant", "SEAP"],
    "PARTNER_RISK_ASSESSMENT": ["ANAF", "ANAF Bilant", "BNR", "BPI", "openapi.ro"],
    "TENDER_OPPORTUNITIES": ["ANAF", "SEAP"],
}

def _calculate_completeness(self, sources: list, analysis_type: str) -> int:
    required = REQUIRED_SOURCES_BY_TYPE.get(analysis_type,
               ["ANAF", "ANAF Bilant", "BNR"])
    found = {s["source_name"] for s in sources if s.get("data_found")}

    found_required = found & set(required)
    score = round(len(found_required) / max(len(required), 1) * 100)

    # Bonus pentru surse extra (max +10)
    extra = found - set(required)
    bonus = min(len(extra) * 2, 10)

    return min(score + bonus, 100)
```

**Complexitate:** Mica | **Impact:** Mare — afecteaza completeness gate si calitatea rapoartelor

---

### 3. `_build_section_prompt()` — Pre-check token budget inainte de construire prompt

**Fisier:** `backend/agents/agent_synthesis.py` — linia ~76-100
**Problema actuala:** Provider routing si token budget se verifica DUPA construirea prompt-ului complet. Daca prompt-ul depaseste limita, s-a irosit timp CPU pe construirea lui. Mai grav, daca datele de intrare sunt foarte mari (ANAF Bilant multi-an), prompt-ul poate depasi memoria.

**Imbunatatire propusa:**
- Estimare rapida a dimensiunii prompt-ului INAINTE de construire
- Daca estimarea depaseste budget, truncheaza datele de intrare (nu prompt-ul)
- Fallback la provider cu context window mai mare daca datele sunt dense

**Exemplu implementare:**
```python
# agent_synthesis.py — adaugare pre-check (~linia 70)
def _estimate_prompt_tokens(self, section_config: dict, data: dict) -> int:
    """Quick estimate without building full prompt."""
    base_tokens = 500  # system prompt + instructions
    data_str = json.dumps(data, default=str)
    data_tokens = len(data_str) // 4  # rough estimate: 4 chars/token
    word_target = section_config.get("word_count", 300)
    output_tokens = word_target * 2  # margin for output
    return base_tokens + data_tokens + output_tokens

async def _generate_section(self, section_key, section_config, verified_data):
    estimated = self._estimate_prompt_tokens(section_config, verified_data)

    # Choose route based on estimated size
    if estimated > 8000:
        route = "quality"  # Claude/Gemini have larger context
    elif estimated > 4000:
        route = "fast"     # Groq/Cerebras can handle
    else:
        route = section_config.get("route_preference", "quality")

    # Truncate data if still too large
    if estimated > 30000:
        verified_data = self._truncate_data(verified_data, max_tokens=20000)

    prompt = self._build_section_prompt(section_key, section_config,
                                         verified_data, route)
    return await self._generate_with_fallback(prompt, route)
```

**Complexitate:** Medie | **Impact:** Mare — previne timeout-uri si esecuri de sinteza

---

### 4. `generate_pdf()` — Encoding diacritice complet + page breaks inteligente

**Fisier:** `backend/reports/pdf_generator.py` — linia ~19-33
**Problema actuala:** Replacements hardcoded pentru diacritice romanesti. Lista e incompleta — lipsesc: ă (cu breve), Ă, î minuscul in anumite contexte Unicode, caractere din surse externe (€, —, ", "). Rezultat: text garbled in PDF-uri.

**Imbunatatire propusa:**
- Folosire `unicodedata.normalize("NFKD")` + fallback map pentru caractere speciale
- Adaugare page break inainte de sectiuni majore (executive summary, financial, risk)
- Word wrapping cu respectare cuvinte (nu taiere la mijloc)

**Exemplu implementare:**
```python
# pdf_generator.py — inlocuire _sanitize (~linia 19-33)
import unicodedata
import textwrap

CHAR_FALLBACK = {
    '\u2013': '-',    # en-dash
    '\u2014': '-',    # em-dash
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
    '\u201e': '"',    # double low-9 quote (Romanian)
    '\u2018': "'",    # left single quote
    '\u2019': "'",    # right single quote
    '\u2026': '...',  # ellipsis
    '\u20ac': 'EUR',  # euro sign
    '\u2022': '*',    # bullet
    '\u00b0': 'o',    # degree
    '\u2122': 'TM',   # trademark
    '\u00a9': '(c)',  # copyright
    '\u00ae': '(R)',  # registered
    '\u2264': '<=',   # less or equal
    '\u2265': '>=',   # greater or equal
}

def _sanitize(text: str) -> str:
    if not text:
        return ""
    # Step 1: NFKD decompose + strip combining marks
    normalized = unicodedata.normalize("NFKD", str(text))
    result = []
    for ch in normalized:
        if ch in CHAR_FALLBACK:
            result.append(CHAR_FALLBACK[ch])
        elif unicodedata.category(ch).startswith("M"):
            continue  # strip combining marks (accents)
        else:
            try:
                ch.encode("latin-1")
                result.append(ch)
            except UnicodeEncodeError:
                result.append("?")
    return "".join(result)


def _smart_word_wrap(text: str, width: int = 55) -> str:
    """Wrap text respecting word boundaries."""
    return textwrap.fill(text, width=width, subsequent_indent="  ")
```

**Complexitate:** Mica | **Impact:** Mediu — calitate vizuala PDF direct vizibila clientului

---

### 5. `generate_html()` — Gradient urgenta Early Warnings + chart fallback

**Fisier:** `backend/reports/html_generator.py` — linia ~443-465
**Problema actuala:** Early warnings din raportul HTML au toate aceeasi culoare indiferent de severitate (rosu). Un warning cu confidence 90% ("firma in insolventa") arata la fel ca unul cu confidence 30% ("posibila scadere angajati"). Nici chart-urile nu au fallback cand lipsesc date de trend.

**Imbunatatire propusa:**
- Gradient de culoare pe baza confidence: rosu (>80%), portocaliu (60-80%), galben (40-60%), gri (<40%)
- Adaugare icon severitate (triangle alert, info circle, etc.)
- Chart fallback: mesaj explicit "Date de trend insuficiente" in loc de sectiune goala

**Exemplu implementare:**
```python
# html_generator.py — inlocuire bloc early warnings (~linia 443)
def _render_early_warning_html(warning: dict) -> str:
    conf = warning.get("confidence", 50)
    if conf >= 80:
        color, bg, icon = "#ef4444", "#451a1a", "&#9888;"  # red, alert
    elif conf >= 60:
        color, bg, icon = "#f97316", "#451f1a", "&#9888;"  # orange
    elif conf >= 40:
        color, bg, icon = "#eab308", "#45351a", "&#9432;"  # yellow, info
    else:
        color, bg, icon = "#94a3b8", "#1e293b", "&#9432;"  # gray

    return f'''
    <div style="border-left: 4px solid {color}; background: {bg};
                padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.2em">{icon}</span>
            <strong style="color:{color}">{warning.get("signal", "Warning")}</strong>
            <span style="color:#94a3b8; font-size:0.85em; margin-left:auto;">
                Confidence: {conf}%
            </span>
        </div>
        <p style="margin:4px 0 0; color:#d1d5db">{warning.get("details", "")}</p>
    </div>'''

# Chart fallback (~linia 155)
def _render_chart_or_fallback(charts_html: list, fallback_msg: str) -> str:
    if charts_html:
        return "\n".join(charts_html)
    return f'<div class="no-data-msg">{fallback_msg}</div>'
```

**Complexitate:** Mica | **Impact:** Mediu — raportul HTML e formatul cel mai folosit pentru vizualizare

---

### 6. Dashboard.tsx — Stat cards cu trend indicator + integration failure links

**Fisier:** `frontend/src/pages/Dashboard.tsx` — linia ~77-115
**Problema actuala:** Stat cards arata doar numere statice (ex: "47 rapoarte"). Nu indica daca e mai mult sau mai putin decat luna trecuta. Integration status arata "OFF" dar fara link direct la Settings pentru configurare.

**Imbunatatire propusa:**
- Adaugare trend indicator pe fiecare stat card (arrow up/down + procent vs luna trecuta)
- Click pe integrare "OFF" → redirect direct la Settings cu scroll la sectiunea relevanta
- Warning banner daca completeness medie < 60% pe ultimele 5 analize

**Exemplu implementare:**
```tsx
// Dashboard.tsx — stat card cu trend (~linia 77)
interface StatCardProps {
  label: string;
  value: number;
  previousValue?: number;
  icon: React.ReactNode;
}

function StatCard({ label, value, previousValue, icon }: StatCardProps) {
  const trend = previousValue ? ((value - previousValue) / previousValue) * 100 : null;

  return (
    <div className="card flex items-center gap-4">
      <div className="p-3 rounded-lg bg-accent-primary/10">{icon}</div>
      <div>
        <p className="text-sm text-gray-400">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
        {trend !== null && (
          <span className={`text-xs ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(0)}% vs. luna trecuta
          </span>
        )}
      </div>
    </div>
  );
}

// Integration link to settings (~linia 104)
function IntegrationItem({ name, active }: { name: string; active: boolean }) {
  const navigate = useNavigate();
  return (
    <div
      className={`flex items-center justify-between py-2 ${!active ? 'cursor-pointer hover:bg-dark-hover rounded px-2' : ''}`}
      onClick={() => !active && navigate('/settings')}
    >
      <span>{name}</span>
      <span className={active ? 'text-green-400' : 'text-red-400 text-xs'}>
        {active ? 'OK' : 'Configureaza →'}
      </span>
    </div>
  );
}
```

**Complexitate:** Mica | **Impact:** Mare — Dashboard-ul e prima pagina vazuta

---

### 7. AnalysisProgress.tsx — Progress granular per agent + ETA

**Fisier:** `frontend/src/pages/AnalysisProgress.tsx` — linia ~124-140
**Problema actuala:** Bara de progres arata doar un procent global (ex: "45%") si un text generic ("Se proceseaza datele"). Utilizatorul nu stie care agent ruleaza, care a terminat, si cat mai dureaza. La analize de 60+ secunde, experienta e frustranta.

**Imbunatatire propusa:**
- Progress breakdown per agent (Agent 1: OK, Agent 4: Running, Agent 5: Waiting)
- ETA estimat bazat pe durata medie a ultimelor 5 analize similare
- Indicatori vizuali per-sursa in Agent 1 (ANAF: done, SEAP: fetching, BPI: failed)

**Exemplu implementare:**
```tsx
// AnalysisProgress.tsx — agent progress breakdown (~linia 130)
interface AgentStatus {
  name: string;
  status: 'waiting' | 'running' | 'done' | 'failed';
  duration_ms?: number;
}

function AgentProgressBar({ agents }: { agents: AgentStatus[] }) {
  const statusIcon = {
    waiting: <Clock className="w-4 h-4 text-gray-500" />,
    running: <Loader className="w-4 h-4 text-accent-secondary animate-spin" />,
    done: <CheckCircle className="w-4 h-4 text-green-400" />,
    failed: <XCircle className="w-4 h-4 text-red-400" />,
  };

  return (
    <div className="space-y-2 mt-4">
      {agents.map(agent => (
        <div key={agent.name} className="flex items-center gap-3 text-sm">
          {statusIcon[agent.status]}
          <span className={agent.status === 'running' ? 'text-white' : 'text-gray-400'}>
            {agent.name}
          </span>
          {agent.duration_ms && (
            <span className="text-gray-500 ml-auto">
              {(agent.duration_ms / 1000).toFixed(1)}s
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ETA display
function ETADisplay({ startTime, progress }: { startTime: number; progress: number }) {
  if (progress <= 5) return null;
  const elapsed = (Date.now() - startTime) / 1000;
  const estimated = (elapsed / progress) * (100 - progress);
  return (
    <span className="text-sm text-gray-400">
      ~{Math.ceil(estimated)}s ramase
    </span>
  );
}
```

**Complexitate:** Medie | **Impact:** Mare — reduce frustrarea pe flow-ul principal

---

### 8. CompareCompanies.tsx — Adaugare grafice comparative + export CSV

**Fisier:** `frontend/src/pages/CompareCompanies.tsx` — linia ~1-252
**Problema actuala:** Comparatia arata DOAR un tabel static. Lipsesc grafice comparative (bar chart CA, radar chart dimensiuni, trend overlay). Export disponibil doar PDF si doar pentru 2 firme.

**Imbunatatire propusa:**
- Bar chart comparativ pentru metrici financiare (CA, profit, angajati)
- Radar chart pentru dimensiunile de risc (suprapuse pe acelasi grafic)
- Export CSV al datelor comparative
- Suport PDF comparativ pentru 3-5 firme (nu doar 2)

**Exemplu implementare:**
```tsx
// CompareCompanies.tsx — grafice comparative (~dupa tabelul de rezultate)
function CompareCharts({ result }: { result: CompareResult }) {
  const companies = result.companies;
  const labels = companies.map(c => c.nume || c.cui);

  // Bar chart - metrici financiare
  const financialData = {
    labels,
    datasets: [
      {
        label: 'Cifra Afaceri (RON)',
        data: companies.map(c => c.cifra_afaceri || 0),
        backgroundColor: '#6366f1',
      },
      {
        label: 'Profit Net (RON)',
        data: companies.map(c => c.profit_net || 0),
        backgroundColor: '#22c55e',
      },
    ]
  };

  // Export CSV
  const exportCSV = () => {
    const headers = ['CUI', 'Nume', 'CAEN', 'CA', 'Profit', 'Angajati', 'Scor Risc'];
    const rows = companies.map(c =>
      [c.cui, c.nume, c.caen, c.cifra_afaceri, c.profit_net, c.angajati, c.scor_risc].join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `comparatie_${Date.now()}.csv`; a.click();
  };

  return (
    <div className="space-y-6 mt-6">
      <div className="card">
        <h3 className="font-semibold mb-4">Comparatie Financiara</h3>
        {/* Render bar chart cu Chart.js / Recharts */}
      </div>
      <button onClick={exportCSV} className="btn-secondary">
        Export CSV
      </button>
    </div>
  );
}
```

**Complexitate:** Medie | **Impact:** Mare — comparatia e feature diferentiator fata de ANAF manual

---

### 9. `run_monitoring_check()` — Detectie combinatii critice + delta financiar

**Fisier:** `backend/services/monitoring_service.py` — linia ~32-45, 175-209
**Problema actuala:** Severitatea alertelor se bazeaza pe o singura schimbare de camp (stare, inactiv, TVA, split_TVA). Combinatia "firma devine inactiva + pierde TVA" ar trebui sa fie CRITICAL, nu doar 2x YELLOW. Plus, nu se detecteaza schimbari financiare (scadere CA, pierderi consecutive).

**Imbunatatire propusa:**
- Matrice de combinatii critice (inactiv+radiat=CRITICAL, tva_lost+split=HIGH)
- Adaugare delta financiar din ANAF Bilant (CA drop >30%, pierdere 2 ani)
- Scoring combinat pe alert (nu doar per-field)

**Exemplu implementare:**
```python
# monitoring_service.py — combinatii critice (~linia 32)
CRITICAL_COMBINATIONS = [
    ({"stare": "RADIAT"}, {"inactiv": True}),        # radiat + inactiv
    ({"stare": "RADIAT"}, {"tva": False}),            # radiat + pierdere TVA
    ({"inactiv": True}, {"tva": False}),              # inactiv + pierdere TVA
]

def _determine_combined_severity(changes: list[dict]) -> str:
    """Check if combination of changes warrants escalation."""
    change_set = {(c["field"], c["new_value"]) for c in changes}

    for combo_a, combo_b in CRITICAL_COMBINATIONS:
        a_match = any((f, v) in change_set for f, v in combo_a.items())
        b_match = any((f, v) in change_set for f, v in combo_b.items())
        if a_match and b_match:
            return "CRITICAL"

    severities = [c.get("severity", "GREEN") for c in changes]
    if "RED" in severities:
        return "RED"
    if severities.count("YELLOW") >= 2:
        return "RED"  # 2+ yellow = escalate
    return max(severities, key=lambda s: ["GREEN", "YELLOW", "RED"].index(s))
```

**Complexitate:** Medie | **Impact:** Mare — previne false negatives pe alerte critice

---

### 10. BatchAnalysis.tsx — Preview CSV + detalii erori per-CUI

**Fisier:** `frontend/src/pages/BatchAnalysis.tsx` — linia ~95-235
**Problema actuala:** CSV-ul se uploadeaza direct fara preview. Utilizatorul nu vede ce CUI-uri sunt invalide pana dupa upload. In timpul procesarii, vede doar "3 failed" fara sa stie CARE au esuat si DE CE.

**Imbunatatire propusa:**
- Preview CSV inainte de upload: lista CUI-uri, validare instant, highlight invalide
- Per-CUI progress list in timpul procesarii (CUI, status, eroare)
- Buton "Retry failed only" care reia doar CUI-urile esuate

**Exemplu implementare:**
```tsx
// BatchAnalysis.tsx — CSV preview (~linia 95)
function CSVPreview({ file, onConfirm }: { file: File; onConfirm: (valid: string[]) => void }) {
  const [rows, setRows] = useState<{ cui: string; valid: boolean; error?: string }[]>([]);

  useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
      const parsed = lines.map(line => {
        const result = validateCUI(line);
        return { cui: line, valid: result.valid, error: result.error };
      });
      setRows(parsed);
    };
    reader.readAsText(file);
  }, [file]);

  const validCount = rows.filter(r => r.valid).length;
  const invalidCount = rows.filter(r => !r.valid).length;

  return (
    <div className="card">
      <h3 className="font-semibold mb-3">Preview CSV — {rows.length} randuri</h3>
      <div className="flex gap-4 mb-3 text-sm">
        <span className="text-green-400">{validCount} valide</span>
        <span className="text-red-400">{invalidCount} invalide</span>
      </div>
      <div className="max-h-60 overflow-y-auto space-y-1">
        {rows.map((row, i) => (
          <div key={i} className={`flex items-center gap-2 text-sm px-2 py-1 rounded
            ${row.valid ? 'text-gray-300' : 'text-red-400 bg-red-900/20'}`}>
            {row.valid ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            <span>{row.cui}</span>
            {row.error && <span className="text-xs text-red-300 ml-auto">{row.error}</span>}
          </div>
        ))}
      </div>
      <button
        className="btn-primary mt-4"
        disabled={validCount === 0}
        onClick={() => onConfirm(rows.filter(r => r.valid).map(r => r.cui))}
      >
        Porneste analiza ({validCount} CUI-uri)
      </button>
    </div>
  );
}
```

**Complexitate:** Medie | **Impact:** Mare — batch e feature-ul cu cea mai mare economie de timp

---

### 11. `_calculate_compare_score()` — Eliminare duplicare scoring Agent 4

**Fisier:** `backend/routers/compare.py` — linia ~142-183
**Problema actuala:** Formula de scoring din compare.py duplica logica din `verification/scoring.py`. Daca se modifica scoring-ul in Agent 4, compare-ul ramane cu formula veche — inconsistenta intre scoruri.

**Imbunatatire propusa:**
- Import si reutilizare `calculate_risk_score()` din `verification/scoring.py`
- Daca scoring-ul Agent 4 necesita date complete, adaugare mod "lite" care functioneaza cu date partiale

**Exemplu implementare:**
```python
# compare.py — inlocuire _calculate_compare_score (~linia 142)
from backend.agents.verification.scoring import calculate_risk_score

def _calculate_compare_score(company_data: dict) -> dict:
    """Use Agent 4 scoring in lite mode for compare consistency."""
    # Build minimal state for scoring
    state = {
        "official_data": {
            "financial": {
                "cifra_afaceri": company_data.get("cifra_afaceri"),
                "profit_net": company_data.get("profit_net"),
                "numar_angajati": company_data.get("numar_angajati"),
                "capitaluri_proprii": company_data.get("capitaluri_proprii"),
            },
            "company": {
                "stare_firma": company_data.get("stare_firma", "ACTIVA"),
                "tva": company_data.get("platitor_tva", False),
                "caen_code": company_data.get("caen"),
            }
        }
    }
    result = calculate_risk_score(state, lite_mode=True)
    return result
```

**Complexitate:** Mica | **Impact:** Mediu — consistenta scoruri in tot sistemul

---

### 12. `NewAnalysis.tsx` — Wizard progress bar + CUI auto-lookup

**Fisier:** `frontend/src/pages/NewAnalysis.tsx` — linia ~1-439
**Problema actuala:** Wizard-ul de 4 pasi nu are indicator vizual de progres (utilizatorul nu stie la ce pas e). CUI-ul se valideaza MOD-11 dar nu se confirma daca firma exista real — utilizatorul afla abia dupa ce analiza esueaza.

**Imbunatatire propusa:**
- Bara de progres vizuala "Pas 1 din 4" cu labels per step
- La introducere CUI valid, auto-lookup ANAF pentru confirmare (numele firmei)
- Template preview: click pe template → descriere ce include raportul

**Exemplu implementare:**
```tsx
// NewAnalysis.tsx — wizard progress bar (~linia 140)
function WizardProgress({ step, steps }: { step: string; steps: string[] }) {
  const currentIndex = steps.indexOf(step);
  const labels = ['Tip analiza', 'Intrebari', 'Nivel', 'Confirmare'];

  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm
            ${i <= currentIndex ? 'bg-accent-primary text-white' : 'bg-dark-surface text-gray-500'}`}>
            {i < currentIndex ? '✓' : i + 1}
          </div>
          <span className={`text-xs hidden sm:block
            ${i <= currentIndex ? 'text-white' : 'text-gray-500'}`}>
            {labels[i]}
          </span>
          {i < steps.length - 1 && (
            <div className={`w-8 h-0.5 ${i < currentIndex ? 'bg-accent-primary' : 'bg-dark-border'}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// CUI auto-lookup (~linia 281)
async function lookupCUI(cui: string): Promise<string | null> {
  try {
    const resp = await fetch(`/api/companies?search=${cui}&limit=1`);
    const data = await resp.json();
    if (data.companies?.length > 0) {
      return data.companies[0].name; // "SC EXAMPLE SRL"
    }
    return null; // CUI valid dar necunoscut in DB
  } catch { return null; }
}
```

**Complexitate:** Mica | **Impact:** Mediu — wizard-ul e punctul de intrare pentru orice analiza

---

### 13. ReportView.tsx — Comparatie cu raportul anterior + metadata raport

**Fisier:** `frontend/src/pages/ReportView.tsx` — linia ~118-380
**Problema actuala:** Raportul se afiseaza izolat fara context temporal. Daca firma a fost analizata de 3 ori, utilizatorul trebuie sa navigheze manual intre rapoarte pentru a vedea diferentele. Lipsesc si metadate utile: durata analiza, freshness date, confidence medie.

**Imbunatatire propusa:**
- Banner "vs. raportul anterior" cu delta: scor risc +5pts, CA -12%, angajati stabili
- Metadata panel: durata analiza, surse OK/total, confidence medie, data celle mai vechi surse
- Link "Vezi istoricul" → CompanyDetail score history

**Exemplu implementare:**
```tsx
// ReportView.tsx — delta banner (~linia 125)
function DeltaBanner({ currentReport, previousReport }: Props) {
  if (!previousReport) return null;

  const scoreDelta = (currentReport.risk_score || 0) - (previousReport.risk_score || 0);
  const dateOld = new Date(previousReport.created_at).toLocaleDateString('ro-RO');

  return (
    <div className="card bg-dark-surface/50 border-accent-primary/30 mb-4">
      <div className="flex items-center gap-2 text-sm">
        <TrendingUp className="w-4 h-4 text-accent-secondary" />
        <span className="text-gray-400">vs. raport din {dateOld}:</span>
        <span className={scoreDelta >= 0 ? 'text-green-400' : 'text-red-400'}>
          Scor risc {scoreDelta >= 0 ? '+' : ''}{scoreDelta} puncte
        </span>
      </div>
    </div>
  );
}

// Metadata panel (~linia 130)
function ReportMetadata({ report }: { report: Report }) {
  const sources = report.sources || [];
  const okCount = sources.filter(s => s.data_found).length;
  const avgConf = report.full_data?.confidence_avg || null;

  return (
    <div className="flex gap-4 text-xs text-gray-400 mb-4">
      <span>Surse: {okCount}/{sources.length}</span>
      {avgConf && <span>Confidence: {avgConf}%</span>}
      <span>Generat in: {report.full_data?.duration_seconds || '?'}s</span>
    </div>
  );
}
```

**Complexitate:** Medie | **Impact:** Mediu — contextul temporal face raportul mult mai util

---

### 14. Layout.tsx — Breadcrumbs + notification bell + global search

**Fisier:** `frontend/src/components/Layout.tsx` — linia ~1-126
**Problema actuala:** Navigatia e flat — nu exista breadcrumbs (utilizatorul nu stie ca e in Dashboard > Company > Report). Nu exista centru de notificari (alertele monitoring ajung doar pe Telegram). Nu exista search global (trebuie sa navighezi la Companies si apoi sa cauti).

**Imbunatatire propusa:**
- Breadcrumbs dinamice pe baza rutei (Dashboard > Companies > SC Example SRL)
- Notification bell cu badge count (alerte monitoring noi, joburi complete)
- Search global (Ctrl+K) cu search instant in companies si reports

**Exemplu implementare:**
```tsx
// Layout.tsx — breadcrumbs (~linia 90)
function Breadcrumbs() {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  const labels: Record<string, string> = {
    'companies': 'Companii',
    'reports': 'Rapoarte',
    'compare': 'Comparator',
    'monitoring': 'Monitorizare',
    'settings': 'Setari',
    'new-analysis': 'Analiza Noua',
    'batch': 'Batch',
  };

  if (segments.length === 0) return null;

  return (
    <div className="flex items-center gap-1 text-sm text-gray-500 mb-4">
      <Link to="/" className="hover:text-white">Dashboard</Link>
      {segments.map((seg, i) => (
        <span key={i} className="flex items-center gap-1">
          <ChevronRight className="w-3 h-3" />
          {i === segments.length - 1
            ? <span className="text-white">{labels[seg] || seg}</span>
            : <Link to={'/' + segments.slice(0, i+1).join('/')} className="hover:text-white">
                {labels[seg] || seg}
              </Link>
          }
        </span>
      ))}
    </div>
  );
}
```

**Complexitate:** Medie | **Impact:** Mare — navigatia afecteaza TOATE paginile

---

### 15. `cache_service.py` — Tiered caching (in-memory L1 + SQLite L2)

**Fisier:** `backend/services/cache_service.py` — linia ~1-227
**Problema actuala:** Toate cache lookups trec prin SQLite (disk I/O). Daca aceeasi firma e accesata de 10 ori in 5 minute (ex: compare + monitoring + batch), SQLite e interogat de 10 ori inutil. Lipseste un layer de cache in-memory pentru hot data.

**Imbunatatire propusa:**
- L1 cache in-memory (dict cu TTL scurt, max 50 entries) pentru CUI-uri accesate recent
- L2 ramane SQLite (ca acum)
- L1 invalidation automata la write in L2

**Exemplu implementare:**
```python
# cache_service.py — L1 in-memory cache (~linia 1)
from collections import OrderedDict
from time import time

class L1Cache:
    """In-memory LRU cache for hot data. Max 50 entries, TTL 5 minutes."""

    def __init__(self, max_size: int = 50, ttl_seconds: int = 300):
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        if key in self._store:
            ts, value = self._store[key]
            if time() - ts < self._ttl:
                self._store.move_to_end(key)
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (time(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

_l1 = L1Cache()

# In get():
async def get(key: str, db) -> Any | None:
    # L1 check first
    cached = _l1.get(key)
    if cached is not None:
        return cached

    # L2 (SQLite) fallback
    row = await db.fetch_one("SELECT data FROM data_cache WHERE ...")
    if row:
        _l1.set(key, row["data"])  # promote to L1
        return row["data"]
    return None
```

**Complexitate:** Medie | **Impact:** Mediu — reduce latenta pe operatii repetitive

---

### 16. Settings.tsx — Test buttons per integrare + quota display

**Fisier:** `frontend/src/pages/Settings.tsx` — linia ~157-266
**Problema actuala:** Doar Telegram are buton "Test". Utilizatorul nu stie daca Tavily, Gemini sau Groq functioneaza pana nu ruleaza o analiza completa. Lipseste si informatia de consum (quota Tavily, openapi.ro).

**Imbunatatire propusa:**
- Buton "Testeaza" pentru fiecare integrare (Tavily, Gemini, Groq, Telegram)
- Afisare quota: "Tavily: 234/1000 cereri luna aceasta"
- Validare format API key inainte de save

**Exemplu implementare:**
```tsx
// Settings.tsx — test per integration (~linia 157)
async function testIntegration(provider: string): Promise<{ok: boolean; msg: string}> {
  try {
    const resp = await fetch(`/api/health/deep`);
    const data = await resp.json();
    const status = data[provider];
    if (status?.ok) return { ok: true, msg: `${provider}: OK (${status.latency_ms}ms)` };
    return { ok: false, msg: `${provider}: ${status?.error || 'Indisponibil'}` };
  } catch (e) {
    return { ok: false, msg: `Eroare la testare: ${(e as Error).message}` };
  }
}

// Quota display component
function QuotaDisplay({ provider, used, total }: Props) {
  const pct = total ? Math.round((used / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
      <div className="flex-1 h-1.5 bg-dark-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${pct > 80 ? 'bg-red-500' : 'bg-accent-primary'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span>{used}/{total} ({pct}%)</span>
    </div>
  );
}
```

**Complexitate:** Medie | **Impact:** Mediu — previne esecuri cauzate de configurari gresite

---

### 17. `orchestrator.py` — Circuit breaker pe agenti + cross-agent validation

**Fisier:** `backend/agents/orchestrator.py` — linia ~75-218
**Problema actuala:** Daca un agent esueaza consistent (ex: Tavily quota depasita), sistemul continua sa-l apeleze la fiecare job, irosind timp. Nu exista nici validare intre agenti (numele firmei din ANAF vs cel din web search pot diferi fara sa fie semnalat).

**Imbunatatire propusa:**
- Circuit breaker: dupa 3 esecuri consecutive per agent, skip pentru 30 minute
- Cross-agent validation: compara company name/CUI intre Agent 1 si Agent 2 output
- Log timing per nod in format structured (pentru dashboard metrics)

**Exemplu implementare:**
```python
# orchestrator.py — circuit breaker (~linia 26)
from collections import defaultdict
from time import time

_agent_failures: dict[str, list[float]] = defaultdict(list)
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_WINDOW = 1800  # 30 min

def _is_circuit_open(agent_name: str) -> bool:
    """Check if agent should be skipped due to repeated failures."""
    failures = _agent_failures[agent_name]
    # Clean old failures
    now = time()
    _agent_failures[agent_name] = [f for f in failures if now - f < CIRCUIT_BREAKER_WINDOW]
    return len(_agent_failures[agent_name]) >= CIRCUIT_BREAKER_THRESHOLD

def _record_failure(agent_name: str):
    _agent_failures[agent_name].append(time())

def _reset_circuit(agent_name: str):
    _agent_failures[agent_name].clear()
```

**Complexitate:** Medie | **Impact:** Mediu — reduce timpii de procesare cand surse sunt down

---

### 18. CompanyDetail.tsx — Monitoring quick-add + peer comparison link

**Fisier:** `frontend/src/pages/CompanyDetail.tsx` — linia ~1-351
**Problema actuala:** Pagina de companie arata profilul si scorurile dar nu ofera actiuni directe: nu poti adauga firma la monitorizare, nu poti vedea firme similare (acelasi CAEN), nu poti compara direct cu un competitor.

**Imbunatatire propusa:**
- Buton "Monitorizeaza" care adauga instant firma la monitoring
- Link "Firme similare (CAEN XXXX)" care deschide Companies filtrat pe CAEN
- Buton "Compara cu..." care deschide CompareCompanies pre-populated

**Exemplu implementare:**
```tsx
// CompanyDetail.tsx — action buttons (~linia 160)
function CompanyActions({ company }: { company: Company }) {
  const navigate = useNavigate();
  const { toast } = useToast();

  const addMonitoring = async () => {
    try {
      await api.createMonitoring({ company_id: company.id });
      toast('Firma adaugata la monitorizare', 'success');
    } catch (e) {
      toast('Eroare: ' + (e as Error).message, 'error');
    }
  };

  return (
    <div className="flex gap-2 mt-4">
      <button onClick={addMonitoring} className="btn-secondary text-sm">
        <Bell className="w-4 h-4" /> Monitorizeaza
      </button>
      <button
        onClick={() => navigate(`/companies?caen=${company.caen_code}`)}
        className="btn-secondary text-sm"
      >
        <Users className="w-4 h-4" /> Firme similare
      </button>
      <button
        onClick={() => navigate(`/compare?cui=${company.cui}`)}
        className="btn-secondary text-sm"
      >
        <GitCompare className="w-4 h-4" /> Compara
      </button>
    </div>
  );
}
```

**Complexitate:** Mica | **Impact:** Mediu — fluenta navigatiei intre functionalitati

---

## PARTEA II — FUNCTII NOI

---

### 1. Global Search (Ctrl+K) — Cautare rapida in tot sistemul

**Descriere:** Command palette (similar VS Code) care cauta simultan in companii, rapoarte si CUI-uri. Se activeaza cu Ctrl+K din orice pagina, returneaza rezultate instant cu navigare directa.

**De ce e util:** Utilizatorul trebuie sa navigheze la pagina Companies si apoi sa caute. Pentru un operator care lucreaza cu 10+ firme/zi, fiecare navigare extra e timp pierdut. Un shortcut global reduce 3 click-uri la 1 comanda.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```tsx
// components/GlobalSearch.tsx
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Building, FileText, X } from 'lucide-react';

interface SearchResult {
  type: 'company' | 'report';
  id: string;
  title: string;
  subtitle: string;
}

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Ctrl+K to open
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const timer = setTimeout(async () => {
      const [companies, reports] = await Promise.all([
        fetch(`/api/companies?search=${encodeURIComponent(query)}&limit=5`).then(r => r.json()),
        fetch(`/api/reports?limit=5`).then(r => r.json()),
      ]);
      const combined: SearchResult[] = [
        ...(companies.companies || []).map((c: any) => ({
          type: 'company' as const, id: c.id,
          title: c.name, subtitle: `CUI: ${c.cui} | ${c.caen_code || ''}`
        })),
        ...(reports.reports || []).filter((r: any) =>
          r.title?.toLowerCase().includes(query.toLowerCase())
        ).map((r: any) => ({
          type: 'report' as const, id: r.id,
          title: r.title, subtitle: r.report_type
        })),
      ];
      setResults(combined);
      setSelected(0);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const go = (result: SearchResult) => {
    setOpen(false); setQuery('');
    navigate(result.type === 'company' ? `/company/${result.id}` : `/report/${result.id}`);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-start justify-center pt-[20vh]"
         onClick={() => setOpen(false)}>
      <div className="w-full max-w-lg bg-dark-card border border-dark-border rounded-xl shadow-2xl"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-4 py-3 border-b border-dark-border">
          <Search className="w-5 h-5 text-gray-400" />
          <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Cauta firma, CUI sau raport..."
            className="flex-1 bg-transparent outline-none text-white" />
          <kbd className="text-xs text-gray-500 px-1.5 py-0.5 border border-dark-border rounded">Esc</kbd>
        </div>
        {results.length > 0 && (
          <div className="py-2 max-h-64 overflow-y-auto">
            {results.map((r, i) => (
              <div key={`${r.type}-${r.id}`}
                className={`flex items-center gap-3 px-4 py-2 cursor-pointer
                  ${i === selected ? 'bg-accent-primary/20' : 'hover:bg-dark-hover'}`}
                onClick={() => go(r)}>
                {r.type === 'company' ? <Building className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                <div>
                  <div className="text-sm text-white">{r.title}</div>
                  <div className="text-xs text-gray-500">{r.subtitle}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {query.length >= 2 && results.length === 0 && (
          <div className="py-6 text-center text-gray-500 text-sm">Niciun rezultat</div>
        )}
      </div>
    </div>
  );
}
```
**Necesita:** Adaugare `<GlobalSearch />` in Layout.tsx. Backend: endpoint-urile de search existente sunt suficiente.

---

### 2. Data Lineage per Sectiune Raport — Provenienta datelor

**Descriere:** Fiecare sectiune de raport (executive summary, financiar, risc, etc.) afiseaza un badge mic cu sursa datelor si data ultimei actualizari. Ex: "Sursa: ANAF Bilant 2024, accesat 15.03.2026 | Confidence: 85%".

**De ce e util:** Clientul final vede un raport narativ dar nu stie daca datele sunt din 2024 sau 2020, daca provin de la ANAF oficial sau din web scraping. Transparenta creste increderea si permite luarea deciziilor informate.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```python
# agent_synthesis.py — adaugare lineage in output (~dupa generare sectiune)
def _attach_lineage(section_key: str, section_text: str, sources: list) -> dict:
    """Attach data lineage metadata to each report section."""
    relevant_sources = _find_sources_for_section(section_key, sources)

    lineage = {
        "text": section_text,
        "sources_used": [
            {
                "name": s["source_name"],
                "trust_level": s.get("trust_level", "ESTIMAT"),
                "accessed_at": s.get("accessed_at"),
                "data_found": s.get("data_found", False),
            }
            for s in relevant_sources
        ],
        "freshness_days": _calc_freshness(relevant_sources),
        "confidence_pct": _calc_section_confidence(relevant_sources),
    }
    return lineage

SECTION_SOURCE_MAP = {
    "executive_summary": ["ANAF", "ANAF Bilant", "openapi.ro"],
    "financial_analysis": ["ANAF Bilant", "BNR"],
    "risk_assessment": ["ANAF", "BPI", "openapi.ro"],
    "market_position": ["SEAP", "Tavily"],
    "competition": ["Tavily", "SEAP"],
}
```

```html
<!-- In HTML report — lineage badge per section -->
<div class="lineage-badge">
  <span class="source-tag oficial">ANAF Bilant 2024</span>
  <span class="source-tag verificat">openapi.ro</span>
  <span class="freshness">Actualizat: 15.03.2026</span>
  <span class="confidence">Confidence: 85%</span>
</div>
```

---

### 3. Notification Center — Centru notificari in-app

**Descriere:** Bell icon in header cu badge count. Click deschide panel cu: joburi finalizate, alerte monitoring, erori, changelog. Persistent in DB, mark-as-read.

**De ce e util:** In prezent, notificarile ajung doar pe Telegram (daca e configurat). Daca utilizatorul nu e pe telefon, pierde informatia. Un centru de notificari in-app asigura ca totul e vizibil.

**Complexitate:** Mare | **Impact:** Mare

**Exemplu implementare:**
```python
# Backend: backend/routers/notifications.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
async def list_notifications(unread_only: bool = False, limit: int = 20):
    query = "SELECT * FROM notifications"
    if unread_only:
        query += " WHERE read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT ?"
    rows = await db.fetch_all(query, (limit,))
    unread_count = await db.fetch_one(
        "SELECT COUNT(*) as c FROM notifications WHERE read_at IS NULL"
    )
    return {"notifications": rows, "unread_count": unread_count["c"]}

@router.put("/{notification_id}/read")
async def mark_read(notification_id: str):
    await db.execute(
        "UPDATE notifications SET read_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), notification_id)
    )

@router.put("/read-all")
async def mark_all_read():
    await db.execute(
        "UPDATE notifications SET read_at = ? WHERE read_at IS NULL",
        (datetime.now(timezone.utc).isoformat(),)
    )
```

```sql
-- Migration: notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- 'job_complete', 'monitoring_alert', 'error', 'info'
    title TEXT NOT NULL,
    message TEXT,
    link TEXT,           -- e.g., '/report/abc-123'
    severity TEXT DEFAULT 'info',  -- 'info', 'warning', 'error', 'success'
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_notif_unread ON notifications(read_at) WHERE read_at IS NULL;
```

---

### 4. Export Raport ca Email — Trimitere directa la client

**Descriere:** Buton "Trimite pe email" in ReportView care deschide un formular simplu (adresa email destinatar, subiect pre-completat, mesaj optional) si trimite raportul PDF/DOCX atasat.

**De ce e util:** Flow-ul actual: genereaza raport → descarca PDF → deschide email → ataseaza → trimite. Cu email integrat: un click. Economie de 2-3 minute per raport livrat.

**Complexitate:** Medie | **Impact:** Mare

**Exemplu implementare:**
```python
# Backend: adaugare in routers/reports.py
@router.post("/{report_id}/send-email")
async def send_report_email(report_id: str, body: EmailSendRequest):
    """Send report as email attachment."""
    report = await db.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not report:
        raise HTTPException(404, "Raport negasit")

    # Attach PDF
    pdf_path = report["pdf_path"]
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(400, "PDF indisponibil")

    await send_email(
        to=body.recipient_email,
        subject=body.subject or f"Raport Analiza - {report['title']}",
        body=body.message or "Va atasam raportul de analiza solicitat.",
        attachments=[pdf_path],
    )
    return {"sent": True}
```

```tsx
// Frontend: SendReportModal component
function SendReportModal({ reportId, title, onClose }: Props) {
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState(`Raport: ${title}`);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const { toast } = useToast();

  const send = async () => {
    setSending(true);
    try {
      await fetch(`/api/reports/${reportId}/send-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_email: email, subject, message }),
      });
      toast('Email trimis cu succes', 'success');
      onClose();
    } catch {
      toast('Eroare la trimitere email', 'error');
    }
    setSending(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center">
      <div className="card w-full max-w-md">
        <h3 className="font-semibold mb-4">Trimite raport pe email</h3>
        <input value={email} onChange={e => setEmail(e.target.value)}
          placeholder="email@exemplu.ro" className="input-field w-full mb-3" />
        <input value={subject} onChange={e => setSubject(e.target.value)}
          className="input-field w-full mb-3" />
        <textarea value={message} onChange={e => setMessage(e.target.value)}
          placeholder="Mesaj optional..." className="input-field w-full mb-4" rows={3} />
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="btn-secondary">Anuleaza</button>
          <button onClick={send} disabled={!email || sending} className="btn-primary">
            {sending ? 'Se trimite...' : 'Trimite'}
          </button>
        </div>
      </div>
    </div>
  );
}
```
**Necesita:** Gmail configurat in Settings (GMAIL_USER + GMAIL_APP_PASSWORD).

---

### 5. Favorites / Watchlist — Lista rapida de firme preferate

**Descriere:** Buton star/favorite pe fiecare companie. Lista de favorite accesibila din Dashboard si sidebar. Permite acces rapid la firmele urmarite fara a cauta de fiecare data.

**De ce e util:** Un operator care lucreaza cu 5-10 clienti recurenti pierde timp cautand aceeasi firma. Favorites = acces instant.

**Complexitate:** Mica | **Impact:** Mediu

**Exemplu implementare:**
```python
# Backend: adaugare coloana in companies
# Migration:
# ALTER TABLE companies ADD COLUMN is_favorite INTEGER DEFAULT 0;

@router.put("/api/companies/{company_id}/favorite")
async def toggle_favorite(company_id: str):
    current = await db.fetch_one(
        "SELECT is_favorite FROM companies WHERE id = ?", (company_id,))
    new_val = 0 if current["is_favorite"] else 1
    await db.execute(
        "UPDATE companies SET is_favorite = ? WHERE id = ?", (new_val, company_id))
    return {"is_favorite": bool(new_val)}
```

```tsx
// Frontend: FavoriteButton component
function FavoriteButton({ companyId, isFav }: { companyId: string; isFav: boolean }) {
  const [fav, setFav] = useState(isFav);
  const toggle = async () => {
    const resp = await fetch(`/api/companies/${companyId}/favorite`, { method: 'PUT' });
    const data = await resp.json();
    setFav(data.is_favorite);
  };
  return (
    <button onClick={toggle} className="p-1 hover:bg-dark-hover rounded">
      <Star className={`w-5 h-5 ${fav ? 'fill-yellow-400 text-yellow-400' : 'text-gray-500'}`} />
    </button>
  );
}
```

---

### 6. Dashboard Widget: Top 5 Risc Crescut — Firme cu deteriorare scor

**Descriere:** Widget pe Dashboard care arata top 5 firme ale caror scor de risc a scazut cel mai mult in ultima luna. Include: nume firma, scor curent, delta, trend arrow.

**De ce e util:** Proactiv — utilizatorul nu trebuie sa verifice manual fiecare firma. Sistemul semnaleaza automat deteriorarile.

**Complexitate:** Mica | **Impact:** Mare

**Exemplu implementare:**
```python
# Backend: GET /api/stats/risk-movers
@router.get("/api/stats/risk-movers")
async def get_risk_movers(limit: int = 5):
    """Get companies with biggest risk score changes (30 days)."""
    rows = await db.fetch_all("""
        SELECT c.id, c.name, c.cui,
               sh_new.numeric_score as current_score,
               sh_old.numeric_score as previous_score,
               (sh_new.numeric_score - sh_old.numeric_score) as delta
        FROM companies c
        JOIN score_history sh_new ON c.id = sh_new.company_id
        LEFT JOIN score_history sh_old ON c.id = sh_old.company_id
            AND sh_old.timestamp < sh_new.timestamp
            AND sh_old.timestamp > datetime('now', '-30 days')
        WHERE sh_new.timestamp = (
            SELECT MAX(timestamp) FROM score_history WHERE company_id = c.id
        )
        AND sh_old.timestamp = (
            SELECT MAX(timestamp) FROM score_history
            WHERE company_id = c.id AND timestamp < sh_new.timestamp
        )
        ORDER BY delta ASC
        LIMIT ?
    """, (limit,))
    return {"movers": rows}
```

---

### 7. Grafice Embeddabile in PDF — Chart.js → Matplotlib in PDF

**Descriere:** In loc de grafice doar in HTML (Chart.js), genereaza grafice ca imagini PNG via matplotlib si le embedd-eaza direct in PDF si DOCX. Tipuri: bar chart CA trend, pie chart dimensiuni risc, line chart scor evolutie.

**De ce e util:** PDF-urile curente sunt text-only. Un grafic in PDF valoreaza cat 1000 de cuvinte pentru clientul final.

**Complexitate:** Mare | **Impact:** Mare

**Exemplu implementare:**
```python
# reports/chart_renderer.py (fisier nou)
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO

def render_financial_trend_chart(years: list, ca_values: list, profit_values: list) -> bytes:
    """Generate financial trend bar chart as PNG bytes."""
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    x = range(len(years))
    width = 0.35

    ax.bar([i - width/2 for i in x], ca_values, width, label='Cifra Afaceri', color='#6366f1')
    ax.bar([i + width/2 for i in x], profit_values, width, label='Profit Net', color='#22c55e')

    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend()
    ax.set_title('Evolutie Financiara')
    ax.yaxis.set_major_formatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K')

    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#16213e')
    ax.tick_params(colors='#94a3b8')
    ax.title.set_color('#e2e8f0')

    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# In pdf_generator.py:
from backend.reports.chart_renderer import render_financial_trend_chart

# ...inside generate_pdf():
chart_bytes = render_financial_trend_chart(years, ca_values, profit_values)
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    f.write(chart_bytes)
    chart_path = f.name

pdf.image(chart_path, x=15, w=180)
os.unlink(chart_path)
```
**Necesita:** `matplotlib` in requirements.txt (pure Python, zero dependinte native Windows).

---

### 8. Endpoint /api/companies/{id}/timeline — Timeline evenimentelor firmei

**Descriere:** API endpoint care returneaza cronologic toate evenimentele legate de o firma: analize efectuate, schimbari scor, alerte monitoring, schimbari status ANAF. Afisare ca timeline vizual in CompanyDetail.

**De ce e util:** In loc sa cauti in rapoarte separate, vezi totul cronologic. "In martie scorult a scazut 10 puncte. In aprilie a fost detectata insolventa."

**Complexitate:** Medie | **Impact:** Mediu

**Exemplu implementare:**
```python
# Backend: GET /api/companies/{id}/timeline
@router.get("/api/companies/{company_id}/timeline")
async def get_company_timeline(company_id: str, limit: int = 50):
    events = []

    # Reports
    reports = await db.fetch_all(
        "SELECT id, report_type, created_at, risk_score FROM reports "
        "WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, 20)
    )
    for r in reports:
        events.append({
            "type": "report", "date": r["created_at"],
            "title": f"Raport generat: {r['report_type']}",
            "detail": f"Scor risc: {r['risk_score']}", "link": f"/report/{r['id']}"
        })

    # Score changes
    scores = await db.fetch_all(
        "SELECT numeric_score, timestamp FROM score_history "
        "WHERE company_id = ? ORDER BY timestamp DESC LIMIT ?",
        (company_id, 20)
    )
    for i, s in enumerate(scores[:-1]):
        prev = scores[i + 1]
        delta = s["numeric_score"] - prev["numeric_score"]
        if abs(delta) >= 5:  # only significant changes
            events.append({
                "type": "score_change", "date": s["timestamp"],
                "title": f"Scor modificat: {prev['numeric_score']} → {s['numeric_score']}",
                "detail": f"Delta: {'+' if delta > 0 else ''}{delta} puncte"
            })

    # Monitoring alerts
    audits = await db.fetch_all(
        "SELECT ma.change_type, ma.severity, ma.timestamp, ma.old_value, ma.new_value "
        "FROM monitoring_audit ma JOIN monitoring_alerts m ON ma.alert_id = m.id "
        "WHERE m.company_id = ? ORDER BY ma.timestamp DESC LIMIT ?",
        (company_id, 20)
    )
    for a in audits:
        events.append({
            "type": "alert", "date": a["timestamp"],
            "title": f"Alerta: {a['change_type']}",
            "detail": f"{a['old_value']} → {a['new_value']} (Severitate: {a['severity']})"
        })

    # Sort by date, newest first
    events.sort(key=lambda e: e["date"], reverse=True)
    return {"events": events[:limit]}
```

---

## PARTEA III — IMBUNATATIRI TEHNICE

---

### T1. SQLite PRAGMA optimizari lipsa

**Problema:** RIS are WAL mode si `synchronous=NORMAL` (corect), dar lipsesc: `cache_size`, `temp_store=MEMORY`, `PRAGMA optimize` periodic pe conexiuni long-lived (scheduler). Pe Windows, mmap poate fi mai lent dar `cache_size=-64000` (64MB) si `temp_store=MEMORY` sunt safe.
**Solutie:** Adaugare in `database.py` la connect: `PRAGMA cache_size = -64000; PRAGMA temp_store = MEMORY;`. In scheduler, periodic `PRAGMA optimize=0x10002`.
**Complexitate:** Mica | **Impact:** Performanta — reduce I/O pe interogari repetitive

---

### T2. Recharts migration (inlocuire Chart.js)

**Problema:** Chart.js nu e React-native — se integreaza prin canvas refs, nu prin componente declarative. Nu beneficiaza de React 19 auto-memoizare. Theming-ul e separat de Tailwind.
**Solutie:** Migrare la Recharts (cel mai popular, tree-shakable, declarativ, theming nativ React). Bundle similar ca size, dar DX superior.
**Complexitate:** Mare | **Impact:** Calitate cod + DX — grafice mai usor de extins si mentinut

---

### T3. Request timeout pe frontend

**Problema:** `api.ts` nu are timeout pe fetch requests. Un endpoint blocat (ex: ANAF slow) blocheaza UI-ul indefinit fara feedback.
**Solutie:** Adaugare `AbortController` cu timeout de 30s pe GET, 120s pe POST. Afisare mesaj "Cererea a expirat" la timeout.
**Complexitate:** Mica | **Impact:** Calitate UX — previne UI blocat

---

### T4. Request deduplication pe frontend

**Problema:** Navigare rapida intre pagini poate genera requesturi duplicate (acelasi GET /api/stats de 3 ori). Nu exista dedup.
**Solutie:** Singleton request map in api.ts: daca request identic (method+url) e deja in-flight, returneaza aceeasi Promise.
**Complexitate:** Mica | **Impact:** Performanta — reduce load pe backend

---

### T5. Error messages user-friendly

**Problema:** Erori HTTP (500, 502, 404) ajung raw la utilizator: "Internal Server Error". Nu indica ce sa faca.
**Solutie:** Map de erori cu mesaje romanesti: `500 → "Eroare server. Incearca din nou in cateva secunde."`, `429 → "Prea multe cereri. Asteapta {retry_after}s."`, `503 → "Serviciu indisponibil temporar."`.
**Complexitate:** Mica | **Impact:** Calitate UX

---

### T6. Trend calculation cu handling missing years

**Problema:** `scoring.py` calculeaza trend pe CA/profit presupunand ani consecutivi. Daca lipsesc date pentru 2018-2019 (firma nu a depus), trend-ul se calculeaza gresit (interpoleaza).
**Solutie:** Detectare gap-uri in serii: daca lipseste >1 an, split in segmente si calculeaza trend doar pe segmentul cel mai recent.
**Complexitate:** Medie | **Impact:** Securitate date — scoruri mai precise

---

### T7. Structured logging unificat

**Problema:** Backend-ul are mix de loguru, print, logger.debug cu formate diferite. Cache_service logheaza hit/miss dar agentii nu logheaza consistent.
**Solutie:** Standardizare format: `logger.bind(module="X", cui="Y").info("action", key=val)`. Toate modulele sa emita structured logs parsabile.
**Complexitate:** Medie | **Impact:** Mentenanta — debugging mai rapid

---

### T8. Provider health tracking

**Problema:** Daca Groq da 429 de 10 ori, sistemul tot incearca Groq pe urmatorul job (pana la timeout + fallback). Nu memoreaza ca Groq e indisponibil.
**Solutie:** Track last_success/last_failure per provider. Daca provider a esuat de 3+ ori in ultimele 30 min, skip direct la urmatorul. Reset la succes.
**Complexitate:** Mica | **Impact:** Performanta — reduce timpii de procesare cu 10-30s cand un provider e down

---

### T9. Compresie cache SQLite

**Problema:** Entries mari din ANAF Bilant (JSON multi-an, ~50KB per entry) ocupa spatiu in data_cache fara compresie.
**Solutie:** Compresie zlib pe valori >1KB inainte de INSERT, decompresie la SELECT. Flag `compressed` in schema.
**Complexitate:** Mica | **Impact:** Performanta — reduce dimensiunea DB si I/O

---

### T10. Accesibilitate frontend (ARIA, contrast, keyboard)

**Problema:** Butoanele si link-urile nu au ARIA labels explicite. Contrast ratios pe dark theme nu sunt verificate WCAG 2.1. Modals nu au focus trap.
**Solutie:** Audit ARIA: adauga `aria-label` pe icon buttons, `role="dialog"` pe modals, `aria-live` pe toast. Verifica contrast ratios cu tool automat.
**Complexitate:** Medie | **Impact:** Calitate — accesibilitate pentru utilizatori cu disabilitati

---

### T11. Dead letter queue pentru batch

**Problema:** CUI-uri care esueaza in batch dupa 2 retry-uri sunt marcate "failed" dar nu se poate face nimic cu ele ulterior (trebuie upload nou CSV).
**Solutie:** Salvare lista CUI-uri esuate in DB cu motiv esec. Endpoint `POST /batch/{id}/retry-failed` care reia doar esuatele.
**Complexitate:** Mica | **Impact:** Calitate — batch mai robust

---

### T12. Zombie company detection in scoring

**Problema:** Firme cu CA=0, angajati=0 dar status ACTIV in ANAF primesc scor mediocru (50-60) in loc de flag rosu. Sunt "zombie companies" — exista pe hartie dar nu opereaza.
**Solutie:** In scoring.py, detectare: CA=0 ultimii 2 ani + angajati=0 → flag "ZOMBIE_COMPANY" + scor operational = 10.
**Complexitate:** Mica | **Impact:** Calitate — scoruri mai precise

---

### T13. data.gov.ro integrare (sursa gratuita suplimentara)

**Problema:** RIS foloseste date publice (ANAF, ONRC, BNR, SEAP) dar ignora data.gov.ro — portalul national de open data cu mii de dataset-uri gratuite (economie, statistici regionale, transparenta bugetara).
**Solutie:** Client nou `datagov_client.py` care interogheaza CKAN API de la data.gov.ro pentru statistici economice regionale per CAEN/judet. Integrat in caen_context.py ca sursa complementara.
**Complexitate:** Mare | **Impact:** Calitate date — date suplimentare gratuite

---

### T14. Backup .env automat inainte de modificari Settings

**Problema:** Endpoint-ul PUT /api/settings modifica .env direct. Daca se introduce o valoare gresita, nu exista backup al configurarii anterioare.
**Solutie:** Inainte de orice write in .env, copiere automata `.env.bak` cu timestamp. Maxim 5 backup-uri rotate.
**Complexitate:** Mica | **Impact:** Securitate — prevenire pierdere configuratie

---

## SUMAR PRIORITATI

| Prioritate | # | Nume | Complexitate | Impact | Categorie |
|---|---|---|---|---|---|
| **P0 — URGENT** | 1 | Corectare ponderare confidence scoring | Mica | Maxim | Backend - Scoring |
| **P0 — URGENT** | 2 | Completeness score dinamic per tip analiza | Mica | Mare | Backend - Agent 1 |
| **P0 — URGENT** | T12 | Zombie company detection | Mica | Mare | Backend - Scoring |
| **P1 — IMPORTANT** | 3 | Pre-check token budget inainte de prompt | Medie | Mare | Backend - Synthesis |
| **P1 — IMPORTANT** | 7 | Progress granular per agent + ETA | Medie | Mare | Frontend - UX |
| **P1 — IMPORTANT** | 6 | Dashboard stat cards cu trend | Mica | Mare | Frontend - UX |
| **P1 — IMPORTANT** | 10 | Batch CSV preview + per-CUI erori | Medie | Mare | Frontend - UX |
| **P1 — IMPORTANT** | 14 | Layout breadcrumbs + notifications | Medie | Mare | Frontend - Nav |
| **P1 — IMPORTANT** | 9 | Monitoring combinatii critice | Medie | Mare | Backend - Alerting |
| **P1 — IMPORTANT** | N1 | Global Search (Ctrl+K) | Medie | Mare | Frontend - Feature |
| **P1 — IMPORTANT** | T8 | Provider health tracking | Mica | Mare | Backend - Perf |
| **P1 — IMPORTANT** | T1 | SQLite PRAGMA optimizari | Mica | Medie | Backend - Perf |
| **P2 — VALOROS** | 4 | PDF encoding diacritice complet | Mica | Mediu | Backend - Reports |
| **P2 — VALOROS** | 5 | HTML early warnings gradient | Mica | Mediu | Backend - Reports |
| **P2 — VALOROS** | 8 | Compare grafice + export CSV | Medie | Mare | Frontend - Feature |
| **P2 — VALOROS** | 11 | Eliminare duplicare scoring compare | Mica | Mediu | Backend - DRY |
| **P2 — VALOROS** | 12 | Wizard progress bar + CUI lookup | Mica | Mediu | Frontend - UX |
| **P2 — VALOROS** | 13 | ReportView delta vs anterior | Medie | Mediu | Frontend - UX |
| **P2 — VALOROS** | 15 | Cache L1 in-memory | Medie | Mediu | Backend - Perf |
| **P2 — VALOROS** | 16 | Settings test per integrare + quota | Medie | Mediu | Frontend - UX |
| **P2 — VALOROS** | 17 | Circuit breaker pe agenti | Medie | Mediu | Backend - Resilienta |
| **P2 — VALOROS** | N2 | Data lineage per sectiune raport | Medie | Mare | Backend - Quality |
| **P2 — VALOROS** | N7 | Grafice in PDF (matplotlib) | Mare | Mare | Backend - Reports |
| **P2 — VALOROS** | T3 | Request timeout frontend | Mica | Mediu | Frontend - Quality |
| **P2 — VALOROS** | T5 | Error messages user-friendly | Mica | Mediu | Frontend - UX |
| **P2 — VALOROS** | T11 | Dead letter queue batch | Mica | Mediu | Backend - Batch |
| **P3 — STRATEGIC** | N3 | Notification Center | Mare | Mare | Full-stack Feature |
| **P3 — STRATEGIC** | N4 | Email report send | Medie | Mare | Full-stack Feature |
| **P3 — STRATEGIC** | N8 | Company timeline endpoint | Medie | Mediu | Backend - Feature |
| **P3 — STRATEGIC** | T2 | Recharts migration | Mare | Mediu | Frontend - Tech |
| **P3 — STRATEGIC** | T6 | Trend calc missing years | Medie | Mediu | Backend - Quality |
| **P3 — STRATEGIC** | T7 | Structured logging unificat | Medie | Mediu | Backend - Maint |
| **P3 — STRATEGIC** | T13 | data.gov.ro integrare | Mare | Mediu | Backend - Data |
| **P4 — NICE-TO-HAVE** | 18 | CompanyDetail monitoring + compare | Mica | Mediu | Frontend - UX |
| **P4 — NICE-TO-HAVE** | N5 | Favorites/Watchlist | Mica | Mediu | Full-stack Feature |
| **P4 — NICE-TO-HAVE** | N6 | Dashboard widget risc crescut | Mica | Mare | Frontend - Feature |
| **P4 — NICE-TO-HAVE** | T4 | Request deduplication frontend | Mica | Mica | Frontend - Perf |
| **P4 — NICE-TO-HAVE** | T9 | Compresie cache SQLite | Mica | Mica | Backend - Perf |
| **P4 — NICE-TO-HAVE** | T10 | Accesibilitate ARIA | Medie | Mediu | Frontend - A11y |
| **P4 — NICE-TO-HAVE** | T14 | Backup .env automat | Mica | Mica | Backend - Safety |

**Total recomandari: 40** (18 imbunatatiri existente + 8 functii noi + 14 tehnice)

---

## NOTE IMPLEMENTARE

1. **Constrangere cost $0:** Toate recomandarile folosesc EXCLUSIV unelte gratuite. Matplotlib e pure Python (zero cost). Recharts e MIT. data.gov.ro e gratuit. Nu se introduce nicio dependinta platita.

2. **Constrangere Windows 10:** Nicio recomandare nu necesita dependinte native complexe. matplotlib functioneaza cu backend Agg (non-GUI). Toate recomandarile au fost validate pentru compatibilitate Windows.

3. **Dependinte intre recomandari:**
   - #11 (DRY scoring) trebuie facut INAINTE de #1 (corectare confidence) — altfel se modifica in 2 locuri
   - #14 (breadcrumbs) trebuie facut INAINTE de N1 (global search) — layout changes
   - T1 (PRAGMA SQLite) e independent si poate fi facut ORICAND
   - N7 (matplotlib PDF) necesita `pip install matplotlib` in requirements.txt

4. **Ce NU se schimba:**
   - Stack-ul (Python + FastAPI + React + SQLite) — confirmat si stabil
   - Structura agentilor (5 agenti LangGraph) — corecta
   - fpdf2 pentru PDF (nu WeasyPrint) — confirmat
   - Tema dark (#1a1a2e) — confirmat
   - Limba UI romana — confirmat
   - Toate cele 37 endpoint-uri existente — neatinse
   - Toate cele 182 teste existente — neatinse

5. **Ordine recomandata de implementare:**
   - Sprint 1 (P0, ~2h): #1, #2, T12 — corectari scoring critice
   - Sprint 2 (P1 backend, ~4h): #3, #9, T8, T1 — robusetea backend
   - Sprint 3 (P1 frontend, ~6h): #6, #7, #10, #14, N1 — UX principal
   - Sprint 4 (P2, ~8h): #4, #5, #8, #11, #12, #13, #15, #16, #17 — polish
   - Sprint 5 (P3, ~10h): N2, N3, N4, N7, N8 — features strategice
   - Sprint 6 (P4, la discretie): restul

6. **Surse cercetare web:**
   - Dashboard UX: UXPin, Julius AI, DesignRush (2025-2026) [CERT]
   - Risk scoring: Cerrix, Flagright, MetricStream, GARP [CERT]
   - React charts: Recharts > Nivo > Visx > TanStack [CERT]
   - SQLite PRAGMA: PowerSync, Forward Email, High Performance SQLite [CERT]
   - AI orchestration: LangGraph best practices, Adopt.ai, SparkCo [CERT]
   - Romanian APIs: data.gov.ro, AlertaCUI.ro, openapi.ro (existente), ListaFirme.eu [CERT/PROBABIL]
   - PDF: fpdf2 confirmat corect, matplotlib pentru grafice [CERT]
