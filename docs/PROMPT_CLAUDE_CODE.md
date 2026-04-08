Ești Claude Code în modul Opus cu efort maxim. Am atașat în acest folder fișierul `SPEC_INTELLIGENCE_SYSTEM.md` care conține specificațiile complete pentru un proiect nou numit **Roland Intelligence System (RIS)**.

**CE VREAU SĂ FACI — ÎN ACEASTĂ ORDINE:**

**PASUL 0 — Citire regulament global**
Înainte de orice altceva, citește regulamentul global din `.claude/rules/` (locația globală Claude Code). Identifică toate regulile, convențiile și preferințele definite acolo — convenții de cod, limbă UI, format fișiere, reguli Git, reguli de siguranță, orice altceva. Toate îmbunătățirile propuse în V2 trebuie să fie aliniate cu aceste reguli. Dacă o sugestie tehnică din specificații intră în conflict cu o regulă globală, semnalezi conflictul explicit și propui varianta conformă.

**PASUL 1 — Citire și înțelegere completă**
Citește integral `SPEC_INTELLIGENCE_SYSTEM.md`. Nu sări nicio secțiune. Înțelege produsul, arhitectura, agenții, tipurile de analiză, baza de date și ordinea de implementare.

**PASUL 2 — Analiză critică**
Identifică și documentează în mintea ta:
- Lacunele tehnice din specificații (ce lipsește pentru o implementare reală)
- Ambiguitățile care ar putea duce la interpretări greșite
- Dependințele nespecificate între componente
- Potențialele probleme de performanță sau scalabilitate
- Tehnologiile propuse care ar putea fi înlocuite cu variante mai potrivite pentru stack-ul ales (Python 3.13 + FastAPI + React 18 + SQLite pe Windows 10)
- Orice aspect tehnic neacoperit care este esențial pentru funcționarea sistemului

**PASUL 3 — Generare SPEC V2**
Generează un fișier nou numit `SPEC_INTELLIGENCE_SYSTEM_V2.md` care conține:

1. **Toate secțiunile originale** — păstrate, completate și îmbunătățite
2. **Secțiuni noi** adăugate de tine pentru aspectele neacoperite identificate la Pasul 2
3. **Completări tehnice concrete** — în special:
   - Schema exactă LangGraph pentru orchestrarea agenților (diagrama de stări și tranziții)
   - Structura exactă de foldere și fișiere a proiectului (tree complet)
   - Requirements.txt complet cu versiunile exacte ale pachetelor
   - Package.json complet pentru frontend
   - Configurarea exactă Playwright pe Windows 10 pentru web scraping
   - Strategia de error handling și retry pentru fiecare agent
   - Cum se gestionează timeout-urile pentru analize lungi (1-4 ore) fără să piardă progresul
   - Strategia de caching (TTL per tip de sursă)
   - Cum funcționează exact WebSocket-ul pentru progress real-time
   - Structura exactă a prompt-urilor per tip de analiză pentru Synthesis Agent
4. **Evaluarea fezabilității** per tip de analiză (TIP 1-9) — ce e implementabil complet, ce are limitări tehnice reale, ce necesită ajustări
5. **Riscuri tehnice identificate** cu soluții propuse
6. **Estimare timp implementare** per fază din Secțiunea 10

**IMPORTANT:**
- Primul pas obligatoriu este citirea regulamentului global `.claude/rules/` — toate propunerile din V2 trebuie să respecte acele reguli
- Nu implementa niciun cod în această fază
- Generează EXCLUSIV documentul V2 cu specificațiile îmbunătățite
- Fii specific și tehnic — nu generalități
- Dacă identifici că o decizie tehnică din V1 este greșită sau suboptimă, spune explicit de ce și propune alternativa corectă
- Dacă o sugestie tehnică intră în conflict cu o regulă din regulamentul global, semnalezi conflictul și propui varianta conformă
- La finalul documentului V2, adaugă o secțiune "ÎNTREBĂRI PENTRU ROLAND" cu orice clarificări pe care le consideri necesare înainte de a începe implementarea
- La finalul documentului V2, adaugă o secțiune "REGULI GLOBALE APLICATE" care listează ce reguli din `.claude/rules/` au influențat deciziile din V2

Confirmă că ai înțeles și începe.
