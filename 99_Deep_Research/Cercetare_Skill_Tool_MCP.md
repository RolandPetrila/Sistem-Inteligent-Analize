# Cercetare: Skill-uri, Tool-uri, MCP-uri — Analiza si Recomandari Globale
**Data:** 2026-04-07 | **Versiune:** 1.0 | **Scope:** Global, independent de proiect
**Surse:** Documentatie oficiala Anthropic, GitHub community, web research 2025-2026

> **Scop document:** Inventar complet al mediului global Claude Code + recomandari de actualizare, imbunatatire, creare, ajustare, eliminare. Fiecare item e autonom si discutabil punctual. Aplicabil oricarui proiect, nu doar celui curent.

---

## CUPRINS

1. [INVENTAR CURENT](#1-inventar-curent)
2. [MCP-URI — Analiza + Recomandari](#2-mcp-uri)
3. [SKILLS (Slash Commands) — Analiza + Recomandari](#3-skills-slash-commands)
4. [HOOKS — Analiza + Recomandari](#4-hooks)
5. [SETTINGS.JSON — Analiza + Recomandari](#5-settingsjson)
6. [CLAUDE.MD Global — Analiza + Recomandari](#6-claudemd-global)
7. [RULES/ — Analiza + Recomandari](#7-rules)
8. [DOCS/ — Analiza + Recomandari](#8-docs)
9. [PRIORITIZARE GLOBALA](#9-prioritizare-globala)
10. [TABEL ACTIUNI](#10-tabel-actiuni)

---

## 1. INVENTAR CURENT

### 1.1 MCP-uri configurate

| # | Nume | Tip | Status | API Key? | Ce face |
|---|------|-----|--------|----------|---------|
| 1 | firecrawl | stdio/npx | ✓ Conectat | Da (fc-*) | Web scraping → Markdown |
| 2 | sequential-thinking | stdio/node | ✓ Conectat | Nu | Gandire pas-cu-pas |
| 3 | context7 | stdio/node | ✓ Conectat | Nu | Docs live per librarie |
| 4 | playwright | stdio/node | ✓ Conectat | Nu | Browser automation |
| 5 | fetch | stdio/node | ✓ Conectat | Nu | HTTP fetch (HTML/JSON/MD) |
| 6 | filesystem | stdio/cmd | ? Netestat | Nu | Acces fisiere locale |
| 7 | memory | stdio/cmd | ? Netestat | Nu | Knowledge graph persistent |
| 8 | github | stdio/bat | ? Neclar | Da (PAT) | GitHub API |
| 9 | brave-search | stdio/bat | ? Neclar | Da (BSA*) | Cautare web |
| 10 | google-docs | stdio/npx | ? Netestat | Da (OAuth) | Google Docs |
| 11 | zapier | http | ! Auth needed | OAuth | 8000+ integrari |

**Total:** 11 MCP-uri configurate | 5 confirmate conectate | 6 status neclar

### 1.2 Skills existente

| # | Comanda | Versiune estimata | Status calitate |
|---|---------|-------------------|-----------------|
| 1 | /audit | matura | ✓ Bun |
| 2 | /checkpoint | matura | ✓ Bun |
| 3 | /deploy | matura | ✓ Bun |
| 4 | /explain | matura | ✓ Bun |
| 5 | /imbunatatiri | matura, complexa | ⚠ Prea vasta |
| 6 | /improve | matura | ⚠ Overlap cu /imbunatatiri |
| 7 | /orchestrator | v2.0, avansata | ✓ Excelent |
| 8 | /plan | matura | ✓ Bun |
| 9 | /research | simpla, eficienta | ✓ Bun |
| 10 | /review | matura | ✓ Bun |
| 11 | /status | rapida | ✓ Bun |
| 12 | /test | matura | ⚠ Partial (nu valideaza coverage real) |

**Total:** 12 skills | 9 solide | 3 cu probleme identificate | 0 eliminate

### 1.3 Hooks existente

| Eveniment | Matcher | Ce face | Status |
|-----------|---------|---------|--------|
| Stop | * (toate) | Log sesiune in session_log.txt | ✓ Activ, dar minimal |

**Total:** 1 hook activ din 27+ evenimente disponibile

### 1.4 Settings.json (global)

| Setare | Valoare curenta | Optim |
|--------|-----------------|-------|
| effortLevel | "medium" | "max" recomandat |
| model | implicit | specificat explicit recomandat |
| permissions.deny | rm -rf, git push --force | OK dar insufficient (nu garantat) |
| permissions.ask | lipsa | recomandat pentru operatii riscante |
| hooks | 1 (Stop logging) | necesita extindere |
| env | lipsa | recomandat pt variabile globale |

### 1.5 Structura globala

```
~/.claude/
  CLAUDE.md          — Regulament global v4.0.0 (comprehensiv)
  settings.json      — Configurare globala
  commands/          — 12 skills
  rules/             — 3 fisiere reguli contextuale
  docs/              — 4 fisiere referinta (debugging, deploy, git, securitate)
  memory/            — Memorie per-proiect (MEMORY.md + fisiere)
  hooks/             — Git hooks (nu Claude hooks)
  session_log.txt    — Log sesiuni
```

---

## 2. MCP-URI

### 2.1 Ce FUNCTIONEAZA bine — PASTREAZA

**M-OK-1: context7** `@upstash/context7-mcp`
- 46.9k stars, activ dezvoltat
- Cel mai util MCP pentru elimina erorile de "API deprecat"
- Verdict: **PASTREAZA, esential**

**M-OK-2: sequential-thinking** `@modelcontextprotocol/server-sequential-thinking`
- Util pentru decizii complexe si debugging
- Verdict: **PASTREAZA**

**M-OK-3: playwright** `@playwright/mcp`
- 30.4k stars, Microsoft maintained
- Singurul mod de a vedea ce vede browserul in realitate
- Verdict: **PASTREAZA, testeaza periodic**

**M-OK-4: fetch** `mcp-fetch-server`
- Util pentru validare endpoint-uri HTTP externe
- Verdict: **PASTREAZA**

**M-OK-5: firecrawl** `firecrawl-mcp`
- Web scraping de calitate, functioneaza
- Verdict: **PASTREAZA (are API key platit)**

---

### 2.2 Ce TREBUIE TESTAT si CLARIFICAT

**M-TEST-1: filesystem** — *instalat azi, netestat*
```
Problema: configurat, dar niciodata verificat functional
Actiune: testeaza cu "listeaza fisierele din directorul curent"
Risc daca nu merge: LOW (fallback pe Read/Glob tools native)
Prioritate: MEDIE
```

**M-TEST-2: memory** — *instalat azi, netestat*
```
Problema: knowledge graph persistent — concept valoros dar nevalidat
Actiune: testeaza cu "salveaza ca entitate: proiect X foloseste Python 3.13"
Risc daca nu merge: LOW (alternative: fisiere memory/ existente)
Prioritate: MEDIE
```

**M-TEST-3: github** — *bat file, status neclar*
```
Problema: configurat prin bat file, nu stim daca conectat
Actiune: verifica cu "listeaza ultimele PR-uri din repo"
Token: ghp_* (verifica daca expirat pe github.com/settings/tokens)
Prioritate: RIDICATA (GitHub = tool zilnic)
```

**M-TEST-4: brave-search** — *bat file, status neclar*
```
Problema: configurat prin bat file, duplica WebSearch nativ
Actiune: testeaza; daca nu merge sau duplica → elimina
Decizie: PASTREAZA doar daca e mai bun decat WebSearch nativ
Prioritate: SCAZUTA
```

**M-TEST-5: google-docs** — *OAuth, netestat*
```
Problema: necesita OAuth flow, poate fi expirat
Actiune: testeaza cu "listeaza documentele mele recente"
Utilitate: MEDIE (Google Docs nu e in workflow zilnic)
Prioritate: SCAZUTA
```

---

### 2.3 Ce LIPSESTE — ADAUGA

**M-NOU-1: SQLite MCP** [ROI: 9/10]
```
Ce: Query direct pe orice baza SQLite din conversatie
De ce: Debug instant, audit date, fara tool extern
Comanda: uvx mcp-server-sqlite --db-path <cale_db>
Blocker: uvx (Python) nu e instalat — instaleaza de la astral.sh/uv
Alternativa npm: @benborla29/mcp-server-sqlite (neverificat)
Efort: MIC (5 min dupa instalare uv)
Prioritate: RIDICATA
Configurare per-proiect (nu global) — calea DB difera
```

**M-NOU-2: Git MCP** [ROI: 8/10]
```
Ce: git log/diff/blame/status din conversatie, history complet
De ce: Review rapid, detectie bug introdus, context istoric
Comanda: uvx mcp-server-git (oficial, Python)
Blocker: same — uvx
Alternativa: git operations via Bash tool (mai lent, manual)
Efort: MIC (dupa uvx instalat)
Prioritate: RIDICATA
Configurare global (functioneaza in orice repo)
```

**M-NOU-3: Time MCP** [ROI: 5/10]
```
Ce: Conversii timezone, calcule temporale, "ce zi e in Tokyo acum?"
De ce: Util la scheduling, timestamps cross-timezone, cron jobs
Comanda: npx -y mcp-server-time --local-timezone=Europe/Bucharest
Blocker: nici unul — npm, instant
Efort: 2 minute
Prioritate: SCAZUTA (nice-to-have, zero friction)
```

**M-NOU-4: GitHub MCP (oficial nou)** [ROI: 8/10]
```
Ce: GitHub API complet — repos, PRs, issues, code search, CI logs
De ce: Versiunea actuala (bat file) e neclar functionala
Sursa: github.com/github/github-mcp-server (28.6k stars)
Comanda: transport HTTP cu GitHub PAT
ATENTIE: pachetul npm vechi @modelcontextprotocol/server-github e DEPRECAT din 04/2025
Configurare:
  "github": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": { "Authorization": "Bearer <GITHUB_PAT>" }
  }
Efort: MIC (15 min inclusiv generare PAT nou)
Prioritate: RIDICATA
```

---

### 2.4 Ce TREBUIE ELIMINAT sau INLOCUIT

**M-DEL-1: brave-search (daca nefunctional)**
```
Motivatie: WebSearch nativ in Claude Code este suficient
Regula: daca nu functioneaza in test → elimina din config
```

**M-DEL-2: github (bat file) → inlocuit cu GitHub oficial HTTP**
```
Motivatie: bat file = fragil, debug greu, token probabil expirat
Inlocuire: GitHub MCP oficial (HTTP transport, mai robust)
```

---

### 2.5 Blocker principal: uvx

**Problema:** SQLite + Git MCP (cele mai valoroase lipsuri) necesita `uvx` (Python).

**Solutie:**
```powershell
# PowerShell — instaleaza uv (Python package manager modern)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Restart terminal, apoi:
uvx --version  # verifica
```

**De ce uv si nu pip?** uv e 10-100x mai rapid, gestioneaza versiuni Python, uvx = npx pentru Python.

---

## 3. SKILLS (Slash Commands)

### 3.1 Ce FUNCTIONEAZA bine — PASTREAZA

**S-OK-1: /audit** — comprehensiv, cu moduri clare (rapid/standard/complet/fix), scor 0-100
**S-OK-2: /checkpoint** — util, 3 moduri, salveaza progresul sesiunii
**S-OK-3: /deploy** — checklist solid, verdict binary READY/NOT READY
**S-OK-4: /explain** — excelent pentru onboarding, 7 pasi clari
**S-OK-5: /orchestrator** — cel mai complex skill, v2.0 cu 15 lectii invatate, self-improving
**S-OK-6: /plan** — solid, validare MINIM/TIPIC/MAXIM inclusa
**S-OK-7: /research** — simplu, eficient, marcheaza [CERT]/[PROBABIL]/[INCERT]
**S-OK-8: /review** — bun, 6 criterii + mode --full pentru pre-commit

---

### 3.2 Ce TREBUIE IMBUNATATIT

**S-FIX-1: /status** — *functional dar prea pasiv*
```
Problema: doar raporteaza, nu detecteaza anomalii
Imbunatatire: adauga detectie activa — TODOs critice, dependinte out-of-date,
              fisiere modificate fara commit, teste care pica
Format imbunatatit:
  [STATUS ACTIV] — probleme detectate automat, nu doar informatii
Efort: MIC (30 min)
Impact: MEDIU
```

**S-FIX-2: /test** — *genereaza teste dar nu valideaza calitatea lor*
```
Problema: genereaza teste, nu ruleaza, nu raporteaza coverage real
Imbunatatire:
  1. Executa testele generate imediat
  2. Raporteaza coverage inainte → dupa (% real din tool)
  3. Identifica module CRITICE fara niciun test (auth, payments, API)
  4. Sugereaza edge cases specifice business logic
Efort: MEDIU (2h)
Impact: RIDICAT
```

**S-FIX-3: /deploy** — *verifica prezenta variabilelor dar nu valideaza valorile*
```
Problema: stie ca ANAF_KEY exista in .env dar nu stie daca e valid
Imbunatatire:
  1. Ping test pentru fiecare API key configurat (HEAD request)
  2. Verifica DB connection (nu doar existenta fisierului)
  3. Verifica ca build-ul generat e sub limita platformei
  4. Detecteaza console.log/print de debug ramase in cod
Efort: MEDIU (2-3h)
Impact: MEDIU
```

**S-FIX-4: /audit** — *bun, dar nu explica impactul business*
```
Problema: gaseste problema la fisier:linie dar nu spune "de ce conteaza"
Imbunatatire:
  - Impact score (1-10) per problema
  - Business risk: "aceasta vulnerabilitate permite X"
  - Timp estimat de remediere per item
Efort: MEDIU (2h)
Impact: MEDIU
```

---

### 3.3 Ce TREBUIE CREAT NOU

**S-NOU-1: /debug** [ROI: 9/10, Prioritate: P0]
```
Ce: Diagnostic sistematic dintr-o eroare sau comportament neasteptat
De ce: Acum debugging = cautare manuala in log-uri. Cu skill: 30s → root cause
Mod de lucru:
  1. Citeste log-uri reale (runtime.log, summary.log, ISSUES.md)
  2. Extrage stack traces complete
  3. Clasifica: IMPORT / NETWORK / DB / AI_PROVIDER / LOGIC / CONFIG / RACE
  4. Root cause cu [CERT]/[PROBABIL]/[INCERT]
  5. Fix concret cu fisier:linie, nu generic
Moduri: auto | startup | api [endpoint] | db | perf | [text liber]
Global: functioneaza pe orice proiect cu log-uri (detecteaza unde sunt)
Efort: MIC (1h)
```

**S-NOU-2: /security** [ROI: 8/10, Prioritate: P1]
```
Ce: Audit securitate exhaustiv OWASP Top 10 + best practices 2025
De ce: /audit face "securitate rapida" — nu suficient pentru aplicatii cu date sensibile
Verifica:
  A1 - Injection (SQL, NoSQL, Command, LDAP)
  A2 - Broken Authentication (session, tokens, MFA)
  A3 - Sensitive Data Exposure (.env in git, logs cu date, console.log)
  A4 - XXE (daca parsezi XML)
  A5 - Broken Access Control (endpoints fara authz)
  A6 - Security Misconfiguration (CORS prea permisiv, debug mode in prod)
  A7 - XSS (dangerouslySetInnerHTML, innerHTML, template injection)
  A8 - Insecure Deserialization
  A9 - Known Vulnerabilities (npm audit, pip audit)
  A10 - Insufficient Logging (ce nu e logat dar ar trebui)
Output: per vulnerabilitate — locatie exacta + exploit scenario + fix + test
Moduri: full | quick | focus [A1-A10] | deps (doar dependinte)
Efort: MEDIU (3-4h)
```

**S-NOU-3: /perf** [ROI: 7/10, Prioritate: P2]
```
Ce: Analiza performanta + identificare bottleneck cu masuratori reale
De ce: Optimizarile fara masuratori sunt ghicite. "Lent" nu e suficient.
Masuratori:
  - Backend: timp per endpoint (ab / wrk / locust)
  - Frontend: Core Web Vitals (LCP, FID, CLS) via Lighthouse CLI
  - DB: query slow log, EXPLAIN ANALYZE
  - Bundle: dimensiune JS/CSS, tree-shaking, code splitting
  - Memory: leak detection, heap snapshots
Output: Top 3 bottleneck-uri cu impact masurabil + plan optimizare prioritizat
Regula: propune fix NUMAI dupa masurare, nu din instinct
Efort: MARE (2 zile prima versiune, updatata per stack)
```

**S-NOU-4: /context** [ROI: 8/10, Prioritate: P1]
```
Ce: Management proactiv al contextului Claude Code pe sesiuni lungi
De ce: Cel mai frecvent mod de esec = context degradat fara sa stii
Functii:
  - /context save [nume] — snapshot complet sesiune curenta (decizii, cod scris, plan)
  - /context restore [nume] — reincarca contextul intr-o sesiune noua
  - /context status — arata cat context e consumat si daca e degradat
  - /context clean — /clear + re-inject context esential
Inspiratie: wshobson/commands context-save/restore
Efort: MEDIU (2h)
Note: diferit de /checkpoint — /checkpoint e pentru progres, /context e pentru continuitate tehnica
```

**S-NOU-5: /docs** [ROI: 6/10, Prioritate: P2]
```
Ce: Generare documentatie din cod (README, API docs, arhitectura)
De ce: Documentatia e mereu in urma. Automatizarea = documentatie actuala
Genereaza:
  - README.md din structura proiect + comentarii
  - API reference din endpoint-uri (OpenAPI/Swagger format)
  - Architecture diagram (text/Mermaid) din fisiere
  - CHANGELOG din git log --oneline
  - JSDoc/docstrings din functii publice
Moduri: readme | api | arch | changelog | full
Efort: MARE (2 zile, stack-dependent)
```

**S-NOU-6: /onboard** [ROI: 8/10, Prioritate: P1]
```
Ce: Primare rapida Claude la inceputul fiecarei sesiuni noi pe un proiect
De ce: Fiecare sesiune noua = Claude nu stie nimic. /onboard = 30s in loc de 5 min de context manual
Citeste si injecteaza:
  - CLAUDE.md per-proiect
  - memory/MEMORY.md + fisierele referentiate
  - Git log ultimele 5 commituri
  - ISSUES.md (daca exista)
  - Starea curenta (porturi, procese active)
Output: "Am inteles. Proiect X, stack Y, ultima modificare Z. Cum pot ajuta?"
Global: detecteaza automat ce e relevant, adapteaza per proiect
Efort: MIC (45 min)
Nota: complementar cu feedback_session_protocol.md deja in memory
```

---

### 3.4 Ce are OVERLAP si trebuie CLARIFICAT

**S-OVERLAP-1: /improve vs /imbunatatiri**
```
Situatie actuala:
  /improve = "upgrade-uri tehnice, versiuni, modernizare"
  /imbunatatiri = "analiza exhaustiva functionala, 8 faze, 30+ recomandari"
  
Problema: utilizatorul nu stie clar cand sa foloseasca care
Solutie propusa: UNIFICA cu mode explicit
  /improve quick    → top 5 quick wins (15 min)
  /improve tehnic   → versiuni, dependinte, patterns (30-60 min)  
  /improve complet  → exhaustiv functional + tehnic (2-3h)
  /improve [aspect] → focus pe un domeniu
  
Alternativa: pastreaza separate dar clarifica in descriere primul rand
Decizie: DE DISCUTAT
```

---

### 3.5 Ce LIPSESTE COMPLET din ecosistem (pattern-uri populare)

Din analiza comunitatii (wshobson/commands, qdhenry/Claude-Command-Suite, awesome-claude-code):

| Pattern popular | Echivalent la noi | Gap |
|-----------------|-------------------|-----|
| context-save/restore | checkpoint (partial) | /context skill lipseste |
| tdd-cycle | /test (partial) | TDD flow nu e explicit |
| feature-development | /plan + implementare | Skill end-to-end feature lipseste |
| onboard | startup protocol in memory | /onboard skill lipseste |
| git-workflow | /review | Automatizare branch/PR lipseste |
| security-scan | /audit (partial) | /security exhaustiv lipseste |

---

## 4. HOOKS

### 4.1 Situatia curenta

**Activ:** 1 hook — `Stop` → log sesiune in session_log.txt (minimal, non-blocant)
**Lipsesc:** Toate celelalte 26+ tipuri de evenimente

**Principiu fundamental (confirmat din surse):**
> CLAUDE.md este advisory (~80% compliance). Hooks sunt deterministe, 100%.
> Tot ce trebuie sa se intample GARANTAT → hook, nu instructiune in CLAUDE.md.

---

### 4.2 Hooks RECOMANDATE — ADAUGA

**H-NOU-1: PostToolUse — Auto-format cod** [ROI: 9/10, Prioritate: P0]
```
Ce: La orice Write/Edit → ruleaza formatter automat (prettier/black/ruff)
De ce: Elimina complet "am uitat sa formatez". Cod mereu consistent.
Config settings.json:
  "PostToolUse": [{
    "matcher": "Write|Edit|MultiEdit",
    "hooks": [{
      "type": "command",
      "command": "~/.claude/hooks/auto-format.sh",
      "timeout": 30,
      "statusMessage": "Formatez...",
      "async": true
    }]
  }]

Script ~/.claude/hooks/auto-format.sh:
  #!/bin/bash
  FILE=$(cat | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))")
  [ -z "$FILE" ] && exit 0
  case "${FILE##*.}" in
    py)   python -m ruff check "$FILE" --fix --silent 2>/dev/null
          python -m black "$FILE" --quiet 2>/dev/null ;;
    ts|tsx|js|jsx)
          npx prettier --write "$FILE" --log-level silent 2>/dev/null ;;
    json) npx prettier --write "$FILE" --parser json --log-level silent 2>/dev/null ;;
  esac
  exit 0

Global: functioneaza pe orice proiect cu Python sau JS/TS
Conditie: ruff + black instalate global (pip install ruff black)
Efort: MIC (30 min)
```

**H-NOU-2: Stop — Notificare Telegram** [ROI: 7/10, Prioritate: P1]
```
Ce: La finalul fiecarei sesiuni → mesaj Telegram cu ce s-a terminat
De ce: Nu mai stai cu ochii pe terminal. Lucrezi la altceva.
Config settings.json:
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "~/.claude/hooks/notify-stop.sh",
      "async": true
    }]
  }]

Script ~/.claude/hooks/notify-stop.sh:
  #!/bin/bash
  INPUT=$(cat)
  ACTIVE=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active','false'))" 2>/dev/null)
  [ "$ACTIVE" = "true" ] && exit 0  # anti-loop infinit!
  
  BOT="$TELEGRAM_BOT_TOKEN"
  CHAT="$TELEGRAM_CHAT_ID"
  [ -z "$BOT" ] || [ -z "$CHAT" ] && exit 0
  
  DIR=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)
  PROJECT=$(basename "$DIR")
  
  curl -s -X POST "https://api.telegram.org/bot${BOT}/sendMessage" \
    -d "chat_id=${CHAT}" \
    -d "text=Claude a terminat in: ${PROJECT}" > /dev/null
  exit 0

Variabile: configureaza TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in settings.json env
Efort: MIC (20 min, inclusiv config env vars)
ATENTIE: stop_hook_active check e OBLIGATORIU — fara el, loop infinit
```

**H-NOU-3: PreToolUse — Guard fisiere sensibile** [ROI: 8/10, Prioritate: P0]
```
Ce: Blocheaza Read pe .env, chei private, fisiere cu parole
De ce: permissions.deny din settings.json NU e garantat (confirmat din surse).
       Hooks cu exit 2 sunt singurul mecanism garantat.
Config:
  "PreToolUse": [{
    "matcher": "Read",
    "hooks": [{
      "type": "command",
      "command": "~/.claude/hooks/guard-sensitive.sh"
    }]
  }]

Script ~/.claude/hooks/guard-sensitive.sh:
  #!/bin/bash
  FILE=$(cat | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))")
  case "$FILE" in
    *.env|*.env.*|*secret*|*.pem|*.key|*id_rsa*|*credentials*)
      echo "BLOCAT: fisier sensibil detectat: $FILE" >&2
      exit 2 ;;
    *)
      exit 0 ;;
  esac

Global: se aplica pe orice proiect, orice context
Efort: MIC (15 min)
```

**H-NOU-4: PreToolUse — Guard comenzi distructive** [ROI: 8/10, Prioritate: P0]
```
Ce: Blocheaza rm -rf, DROP TABLE, DELETE fara WHERE, git push --force
De ce: permissions.deny nu e garantat. Hook e deterministic.
Config: similar H-NOU-3 dar matcher "Bash"

Script ~/.claude/hooks/guard-destructive.sh:
  #!/bin/bash
  CMD=$(cat | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))")
  if echo "$CMD" | grep -qE 'rm -rf|DROP TABLE|DELETE FROM .* WHERE 1|git push --force|git reset --hard'; then
    echo "BLOCAT: comanda distructiva detectata. Confirma manual." >&2
    exit 2
  fi
  exit 0

Efort: MIC (15 min)
```

**H-NOU-5: PostToolUse — Auto-test la modificari critice** [ROI: 7/10, Prioritate: P2]
```
Ce: Dupa modificarea fisierelor critice (auth, payments, API) → ruleaza testele aferente
De ce: Regresii detectate imediat, nu la deploy
Conditie: detecteaza framework de test (pytest/vitest/jest) si ruleaza specific
Efort: MEDIU (2h, logic de detectie per stack)
Nota: poate fi prea zgomotos — testeaza cu timeout scurt
```

**H-NOU-6: PreCompact — Git backup** [ROI: 6/10, Prioritate: P2]
```
Ce: Inainte de compactarea contextului → git commit automat
De ce: La compactare, contextul detaliat se pierde — commit = backup al starii
Script:
  git add -A && git commit -m "auto: pre-compact snapshot" --no-verify 2>/dev/null || true
Efort: MIC (10 min)
Risc: poate crea commituri nedorite — evalueaza per stil de lucru
```

---

### 4.3 Hooks de EVITAT

**H-EVITA-1: Stop hook care blocheaza (exit 2) fara check stop_hook_active**
```
Pericol: Loop infinit garantat
Exemplu gresit: Stop hook care ruleaza teste si returneaza exit 2 daca pica
                → Claude incearca sa repare → Stop din nou → test pica → loop
Regula: ORICE Stop hook care poate returna exit 2 TREBUIE sa verifice stop_hook_active
```

**H-EVITA-2: Hooks sincrone grele pe PostToolUse**
```
Pericol: Fiecare editare devine lenta daca hook-ul dureaza 10+ secunde
Solutie: async: true pe hook-urile care nu trebuie sa blocheze
```

---

## 5. SETTINGS.JSON

### 5.1 Configurare curenta (probleme identificate)

**SET-FIX-1: effortLevel "medium" → "max"**
```
Situatie: effortLevel: "medium" = balansare viteza/calitate
Problema: pentru lucru profesional serios, "max" = extended thinking activ, calitate superioara
Exceptie: "medium" poate fi pastrat daca viteza e prioritara
Recomandare: "max" global, override local daca necesar
Risc: sesiuni mai lente (10-30%)
```

**SET-FIX-2: permissions.deny nu e suficient pentru securitate**
```
Situatie: deny pe rm -rf si git push --force
Problema: confirmata din surse — permissions.deny e "frequently ignored"
Solutie: INLOCUIESTE cu hooks PreToolUse (guard-destructive.sh) pentru garantie reala
Pastreaza deny ca layer secundar, dar nu te baza pe el
```

**SET-FIX-3: lipsa permissions.ask**
```
Situatie: lipseste complet
Problema: operatii riscante (rm, sudo, git push) se executa fara confirmare
Adauga:
  "ask": [
    "Bash(rm *)",
    "Bash(sudo *)",
    "Bash(git push *)",
    "Bash(git reset --hard *)",
    "Bash(npm publish *)",
    "Bash(pip install *)"
  ]
```

**SET-FIX-4: lipsa env globale**
```
Situatie: variabile de mediu nu sunt injectate global
Problema: Telegram bot token, API keys trebuie configurate per-sesiune
Adauga in settings.json:
  "env": {
    "TELEGRAM_BOT_TOKEN": "<token>",
    "TELEGRAM_CHAT_ID": "<chat_id>",
    "PYTHONDONTWRITEBYTECODE": "1",
    "FORCE_COLOR": "1",
    "BASH_DEFAULT_TIMEOUT_MS": "30000"
  }
Atentie: settings.json per-proiect poate fi comis in git — NU pune tokeni acolo
         Tokeni → settings.local.json (gitignored) sau settings.json global user
```

**SET-FIX-5: model nu e specificat explicit**
```
Situatie: model implicit (probabil sonnet based pe config)
Recomandare: specifica explicit pentru predictibilitate
  "model": "claude-opus-4-6",
  "smallModel": "claude-haiku-4-5-20251001"
```

---

### 5.2 Structura settings recomandata (template global)

```json
{
  "model": "claude-opus-4-6",
  "smallModel": "claude-haiku-4-5-20251001",
  "effortLevel": "max",
  
  "permissions": {
    "allow": [
      "Read(*)",
      "Glob(*)",
      "Grep(*)",
      "Edit(*)",
      "Write(*)",
      "Bash(git status)",
      "Bash(git log *)",
      "Bash(git diff *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(npm run *)",
      "Bash(npx *)",
      "Bash(python -m pytest *)",
      "Bash(python -m ruff *)",
      "Bash(python -m black *)"
    ],
    "ask": [
      "Bash(rm *)",
      "Bash(sudo *)",
      "Bash(git push *)",
      "Bash(git reset --hard *)",
      "Bash(npm publish *)",
      "Bash(pip install *)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(git push --force *)",
      "Bash(curl * | bash)",
      "Bash(wget * | sh)"
    ]
  },
  
  "env": {
    "PYTHONDONTWRITEBYTECODE": "1",
    "FORCE_COLOR": "1",
    "BASH_DEFAULT_TIMEOUT_MS": "30000",
    "TELEGRAM_BOT_TOKEN": "<din settings.local.json>",
    "TELEGRAM_CHAT_ID": "<din settings.local.json>"
  },
  
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [{ "type": "command", "command": "~/.claude/hooks/guard-sensitive.sh" }]
      },
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "~/.claude/hooks/guard-destructive.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{ "type": "command", "command": "~/.claude/hooks/auto-format.sh", "async": true }]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "echo [$(date '+%Y-%m-%d %H:%M')] Session ended in: $(pwd) >> ~/.claude/session_log.txt", "async": true },
          { "type": "command", "command": "~/.claude/hooks/notify-stop.sh", "async": true }
        ]
      }
    ]
  },
  
  "cleanupPeriodDays": 30,
  "includeCoAuthoredBy": true,
  "autoUpdatesChannel": "latest"
}
```

**Nota importanta:** Variabilele sensibile (Telegram token, API keys) → `~/.claude/settings.local.json` (gitignored, nu intra in git niciodata).

---

## 6. CLAUDE.MD GLOBAL

### 6.1 Situatia curenta

**Versiune:** 4.0.0 | Estimat: 250-300 linii | Comprehensiv

**Puncte forte:**
- Identitate clara (consultant senior, nu executor)
- Regula suprema de clarificare bine definita
- R1-R6 + R-RISK + R-SEC + R-RECOVERY — acoperire buna
- Auto-update memory definit

**Probleme identificate:**

**CM-FIX-1: Lungime probabil prea mare**
```
Studiu din surse: ~150-200 instructiuni = limita practica de compliance
Dupa aceasta limita, regulile suplimentare au compliance scazut
Test: "daca sterg aceasta sectiune, Claude face greseli concrete?" 
      Daca NU → sterge
Actiune: audit CLAUDE.md cu acest test per sectiune
```

**CM-FIX-2: Lipseste sectiunea de context management proactiv**
```
Situatie curenta: nu e mentionat /clear, /compact, context degradat
Problema: pe sesiuni lungi, calitatea raspunsurilor scade fara ca userul sa stie
Adauga:
  ## MANAGEMENT CONTEXT
  - La task nou independent → sugereaza /clear
  - La 50+ mesaje in sesiune → ruleaza /compact
  - La raspunsuri incoerente → semnaleaza degradare context
```

**CM-FIX-3: Lipseste definitia explicita a "proiect serios"**
```
Situatie: rule 01_project_and_quality.md propune creare CLAUDE.md daca "proiect serios"
Problema: ce e "serios"? Fara definitie, decizia e arbitrara
Adauga criteriu:
  Proiect serios = are >2 module interdependente SAU >500 linii cod SAU e shared cu altii
```

---

### 6.2 Structura recomandata — modularizare

**CM-NOU-1: Modularizare cu @import**
```
Situatie curenta: un fisier monolitic
Alternativa recomandata:
  ~/.claude/CLAUDE.md → importa module
  ~/.claude/rules/01_identity.md
  ~/.claude/rules/02_clarification.md
  ~/.claude/rules/03_code_quality.md
  ~/.claude/rules/04_security.md
  ~/.claude/rules/05_risk_classification.md
  ~/.claude/rules/06_recovery.md

Avantaj: fiecare modul poate fi actualizat independent
         CLAUDE.md ramine sub 50 linii (doar imports + override-uri)
Dezavantaj: @import feature poate fi netestat/nestabil — verifica mai intai
```

---

## 7. RULES/

### 7.1 Situatia curenta (3 fisiere)

**01_project_and_quality.md** — Bun. Quality gates pre-scriere si pre-delete.
**02_suggestions.md** — Bun. Tabela situatii → sugestii contextuale.
**03_reference_docs.md** — Bun. Docs on-demand, nu la start.

### 7.2 Ce LIPSESTE

**R-NOU-1: 04_memory_protocol.md**
```
Ce: Reguli clare pentru cand si ce sa salveze in memory/
De ce: Acum memory-ul e lasat la discretia lui Claude, inconsistent
Continut:
  - Cand salvezi: bug SEV1/SEV2 rezolvat, decizie tehnica confirmata, user feedback
  - Cand NU salvezi: decizii in curs, info neverificata, detalii temporare
  - Format obligatoriu: name, description, type, body cu Why + How to apply
  - Verificare: inainte de a recomanda din memory, verifica ca fisierul/functia exista inca
  - Stale memory: la conflict memory vs realitate → actualizeaza memory, nu actiona pe info veche
```

**R-NOU-2: 05_performance_awareness.md**
```
Ce: Reguli pentru a nu degrada performanta prin solutii evidente dar ineficiente
De ce: Claude sugereaza uneori solutii corecte dar lente (N+1 queries, sync in async)
Continut:
  - La orice loop cu DB call → semnaleaza N+1
  - La orice sync I/O in context async → semnaleaza blocare
  - La orice fetch fara cache → intreaba daca ar trebui cache-uit
  - La orice regex complex → semnaleaza compilare per-call
```

---

## 8. DOCS/

### 8.1 Situatia curenta (4 fisiere)

**debugging.md** — Bun. Workflow 6 pasi + raport bug optim + greseli frecvente.
**deploy.md** — Bun. Checklist + platforme (Vercel, Firebase, Railway, Render).
**git.md** — Bun. Comenzi esentiale + conventional commits + branch strategy.
**securitate.md** — Bun. Ce NU expui + fisiere periculoase + recuperare expunere.

### 8.2 Ce LIPSESTE

**D-NOU-1: performance.md**
```
Ce: Referinta rapida pentru analiza performanta + tool-uri de profiling
De ce: Lipseste complet. Cand apare "e lent", nu exista ghid de investigat.
Continut:
  - Backend: profiling Python (cProfile, py-spy), DB slow queries
  - Frontend: Lighthouse CLI, bundle analysis (webpack-bundle-analyzer, vite-bundle-viz)
  - HTTP: ab, wrk, locust pentru load testing
  - Memory: tracemalloc, memray pentru Python; Chrome DevTools pentru JS
  - Regula 80/20: gaseste ce consuma 80% din timp, optimizeaza aia
```

**D-NOU-2: mcp-guide.md**
```
Ce: Ghid rapid de utilizare MCP-uri configurate + exemple practice
De ce: MCPs sunt invizibile — userul nu stie cand si cum sa le foloseasca
Continut:
  - Lista MCP-uri active + ce pot face concret
  - Exemple de prompturi care activeaza fiecare MCP
  - Cum verifici ca un MCP functioneaza
  - Cum adaugi un MCP nou (npm vs uvx vs HTTP)
  - Troubleshooting: MCP Failed to connect
```

**D-NOU-3: hooks-guide.md**
```
Ce: Ghid hooks configurate + cum se adauga/modifica
De ce: Hooks sunt transparente — userul nu stie ce ruleaza in background
Continut:
  - Lista hooks active + ce fac
  - Cum testezi un hook manual
  - Exit codes: 0 = ok, 2 = blochează, altceva = non-blocant
  - Anti-pattern: stop_hook_active check obligatoriu
  - Locatie scripturi: ~/.claude/hooks/
```

---

## 9. PRIORITIZARE GLOBALA

### P0 — Implementeaza imediat (impact zilnic, efort mic)

| # | Item | Tip | Efort | Impact |
|---|------|-----|-------|--------|
| 1 | H-NOU-3: Guard fisiere sensibile (hook) | Hook | 15 min | Securitate garantata |
| 2 | H-NOU-4: Guard comenzi distructive (hook) | Hook | 15 min | Protectie garantata |
| 3 | H-NOU-1: Auto-format cod (hook) | Hook | 30 min | Calitate consistenta |
| 4 | SET-FIX-3: permissions.ask | Settings | 5 min | Confirmare operatii riscante |
| 5 | M-TEST-3: Verifica/inlocuieste GitHub MCP | MCP | 30 min | GitHub functional |

### P1 — Saptamana urmatoare

| # | Item | Tip | Efort | Impact |
|---|------|-----|-------|--------|
| 6 | S-NOU-1: /debug skill | Skill | 1h | Debugging 10x mai rapid |
| 7 | S-NOU-6: /onboard skill | Skill | 45 min | Start sesiune fara friction |
| 8 | H-NOU-2: Notificare Telegram (hook) | Hook | 20 min | Confort lucru |
| 9 | M-NOU-4: GitHub MCP oficial (HTTP) | MCP | 15 min | GitHub API complet |
| 10 | SET-FIX-1: effortLevel → "max" | Settings | 2 min | Calitate raspunsuri |

### P2 — Luna urmatoare

| # | Item | Tip | Efort | Impact |
|---|------|-----|-------|--------|
| 11 | S-NOU-2: /security skill | Skill | 3-4h | Audit OWASP exhaustiv |
| 12 | S-NOU-4: /context skill | Skill | 2h | Continuitate sesiuni |
| 13 | M-NOU-1: SQLite MCP (dupa uvx) | MCP | 5 min | Debug DB instant |
| 14 | M-NOU-2: Git MCP (dupa uvx) | MCP | 5 min | History complet |
| 15 | R-NOU-1: 04_memory_protocol.md | Rule | 30 min | Memory consistent |
| 16 | S-FIX-2: /test imbunatatit | Skill | 2h | Coverage real |

### P3 — Viitor (conditional)

| # | Item | Tip | Conditie |
|---|------|-----|---------|
| 17 | S-NOU-3: /perf skill | Skill | Daca performanta devine blocant |
| 18 | S-NOU-5: /docs skill | Skill | Daca documentatia e necesara extern |
| 19 | CM-NOU-1: Modularizare CLAUDE.md | CLAUDE.md | Daca @import e stabil |
| 20 | H-NOU-5: Auto-test la modificari critice | Hook | Dupa ce /test e imbunatatit |
| 21 | Blocker uvx: instaleaza astral.sh/uv | Infrastructura | Necesar pentru P2 M-NOU-1/2 |

---

## 10. TABEL ACTIUNI

| ID | Item | Actiune | Tip | Prioritate | Efort | Status |
|----|------|---------|-----|-----------|-------|--------|
| M1 | context7 | PASTREAZA | MCP | — | — | ✓ OK |
| M2 | sequential-thinking | PASTREAZA | MCP | — | — | ✓ OK |
| M3 | playwright | PASTREAZA | MCP | — | — | ✓ OK |
| M4 | fetch | PASTREAZA | MCP | — | — | ✓ OK |
| M5 | firecrawl | PASTREAZA | MCP | — | — | ✓ OK |
| M6 | filesystem | TESTEAZA | MCP | MEDIE | 5 min | ? |
| M7 | memory | TESTEAZA | MCP | MEDIE | 5 min | ? |
| M8 | github (bat) | INLOCUIESTE cu oficial HTTP | MCP | RIDICATA | 30 min | ⚠ |
| M9 | brave-search | TESTEAZA, elimina daca duplica | MCP | SCAZUTA | 10 min | ? |
| M10 | google-docs | TESTEAZA | MCP | SCAZUTA | 10 min | ? |
| M11 | SQLite MCP | ADAUGA (dupa uvx) | MCP | RIDICATA | 5 min | ⬜ |
| M12 | Git MCP | ADAUGA (dupa uvx) | MCP | RIDICATA | 5 min | ⬜ |
| M13 | Time MCP | ADAUGA | MCP | SCAZUTA | 2 min | ⬜ |
| M14 | uvx/uv | INSTALEAZA (blocker) | Infra | RIDICATA | 5 min | ⬜ |
| S1 | /audit | PASTREAZA | Skill | — | — | ✓ |
| S2 | /checkpoint | PASTREAZA | Skill | — | — | ✓ |
| S3 | /deploy | IMBUNATATESTE (ping API keys) | Skill | P2 | 2h | ⬜ |
| S4 | /explain | PASTREAZA | Skill | — | — | ✓ |
| S5 | /imbunatatiri | CLARIFICA overlap cu /improve | Skill | P2 | 1h | ⬜ |
| S6 | /improve | CLARIFICA overlap cu /imbunatatiri | Skill | P2 | 1h | ⬜ |
| S7 | /orchestrator | PASTREAZA | Skill | — | — | ✓ |
| S8 | /plan | PASTREAZA | Skill | — | — | ✓ |
| S9 | /research | PASTREAZA | Skill | — | — | ✓ |
| S10 | /review | PASTREAZA | Skill | — | — | ✓ |
| S11 | /status | IMBUNATATESTE (detectie activa) | Skill | P2 | 30 min | ⬜ |
| S12 | /test | IMBUNATATESTE (run + coverage real) | Skill | P2 | 2h | ⬜ |
| S13 | /debug | CREAZA NOU | Skill | P1 | 1h | ⬜ |
| S14 | /onboard | CREAZA NOU | Skill | P1 | 45 min | ⬜ |
| S15 | /context | CREAZA NOU | Skill | P1 | 2h | ⬜ |
| S16 | /security | CREAZA NOU | Skill | P2 | 3-4h | ⬜ |
| S17 | /perf | CREAZA NOU | Skill | P3 | 2 zile | ⬜ |
| S18 | /docs | CREAZA NOU | Skill | P3 | 2 zile | ⬜ |
| H1 | Stop (logging) | PASTREAZA + extinde | Hook | — | — | ✓ |
| H2 | Guard fisiere sensibile | CREAZA NOU | Hook | P0 | 15 min | ⬜ |
| H3 | Guard comenzi distructive | CREAZA NOU | Hook | P0 | 15 min | ⬜ |
| H4 | Auto-format cod | CREAZA NOU | Hook | P0 | 30 min | ⬜ |
| H5 | Notificare Telegram | CREAZA NOU | Hook | P1 | 20 min | ⬜ |
| H6 | PreCompact git backup | CREAZA NOU | Hook | P2 | 10 min | ⬜ |
| H7 | Auto-test la modificari critice | CREAZA NOU | Hook | P3 | 2h | ⬜ |
| C1 | effortLevel → "max" | AJUSTEAZA | Settings | P1 | 2 min | ⬜ |
| C2 | permissions.ask | ADAUGA | Settings | P0 | 5 min | ⬜ |
| C3 | permissions.deny → hooks | MIGRA | Settings | P0 | 15 min | ⬜ |
| C4 | env globale (Telegram etc.) | ADAUGA | Settings | P1 | 10 min | ⬜ |
| C5 | model explicit | SPECIFICA | Settings | P1 | 2 min | ⬜ |
| R1 | 01_project_and_quality.md | PASTREAZA | Rule | — | — | ✓ |
| R2 | 02_suggestions.md | PASTREAZA | Rule | — | — | ✓ |
| R3 | 03_reference_docs.md | PASTREAZA | Rule | — | — | ✓ |
| R4 | 04_memory_protocol.md | CREAZA NOU | Rule | P2 | 30 min | ⬜ |
| R5 | 05_performance_awareness.md | CREAZA NOU | Rule | P2 | 30 min | ⬜ |
| D1 | debugging.md | PASTREAZA | Doc | — | — | ✓ |
| D2 | deploy.md | PASTREAZA | Doc | — | — | ✓ |
| D3 | git.md | PASTREAZA | Doc | — | — | ✓ |
| D4 | securitate.md | PASTREAZA | Doc | — | — | ✓ |
| D5 | performance.md | CREAZA NOU | Doc | P2 | 1h | ⬜ |
| D6 | mcp-guide.md | CREAZA NOU | Doc | P2 | 1h | ⬜ |
| D7 | hooks-guide.md | CREAZA NOU | Doc | P2 | 1h | ⬜ |

---

## SURSE

- [Anthropic Hooks Reference](https://code.claude.com/docs/en/hooks) — documentatie oficiala, toate hook events
- [Anthropic Settings Reference](https://code.claude.com/docs/en/settings) — settings.json complet
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — 83.1k stars, MCP oficial
- [github/github-mcp-server](https://github.com/github/github-mcp-server) — 28.6k stars, GitHub MCP oficial
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) — 30.4k stars
- [upstash/context7-mcp](https://github.com/upstash/context7-mcp) — 46.9k stars
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — colectie curata comunitate
- [wshobson/commands](https://github.com/wshobson/commands) — 57 comenzi production-ready
- [qdhenry/Claude-Command-Suite](https://github.com/qdhenry/Claude-Command-Suite) — 216+ comenzi
- [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) — 135 agents, 35 skills
- [claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) — exemple avansate hooks
- [Top 15 MCP Servers 2026](https://dev.to/jangwook_kim_e31e7291ad98/top-15-mcp-servers-every-developer-should-install-in-2026-n1h)
- [Hooks production patterns](https://www.pixelmojo.io/blogs/claude-code-hooks-production-quality-ci-cd-patterns)
- [Settings.json Complete Guide 2026](https://www.eesel.ai/blog/settings-json-claude-code)
- [builder.io 50 tips Claude Code](https://www.builder.io/blog/claude-code-tips-best-practices)

---

*Document generat: 2026-04-07 | Urmatoarea revizuire recomandata: dupa implementarea P0-P1*
