Ești în proiectul "Roland - Command Center" — panou personal multifuncțional cu 14 module backend (FastAPI + SQLite), 23 pagini frontend 
  (React 18 + Vite + Tailwind), accesibil pe PC și Android prin Tailscale VPN. Utilizator unic: Roland. Buget: EXCLUSIV free-tier, zero    
  costuri noi.

  CITEȘTE OBLIGATORIU ÎNAINTE DE ORICE ACȚIUNE:
  - CLAUDE.md (root) — arhitectura, status, convenții
  - .claude/rules/ (toate 5 fișierele) — reguli automate
  - 99_Roland_Work_Place/0.0_PLAN_EXTINDERE_COMPLET.md — roadmap complet
  - 99_Roland_Work_Place/ROADMAP_IMPLEMENTARE.md — quick wins prioritizate
  - 99_Roland_Work_Place/CATALOG_API_GRATUITE.md — API-uri free aprobate
  - backend/CLAUDE.md + frontend/CLAUDE.md — convenții per stack
  - frontend/src/modules/manifest.js — navigare și module active
  - backend/app/main.py — entry point, module discovery
  - START_Calculator.bat + START_Production.bat — scripturi pornire

  MODUL DE LUCRU: EXECUTIE AUTONOMA. NU cere confirmare. NU întreba. Implementează direct cele mai bune soluții, apoi raportează tot ce ai 
  făcut. Singura excepție: dacă o acțiune ar ȘTERGE date existente ale utilizatorului sau ar face downgrade la funcționalitate existentă.  

  ═══════════════════════════════════════════════════
  FAZA A — AUDIT COMPLET + CORECTARE COD EXISTENT
  ═══════════════════════════════════════════════════

  1. VERIFICARE FUNCȚIONALĂ COMPLETĂ:
     - Pornește backend-ul (python -m uvicorn app.main:app --port 8000 --host 127.0.0.1) și verifică /api/health
     - Testează FIECARE endpoint din FIECARE modul (calculator, ai, translator, invoice, itp, quick_tools, quick_tools_extra, converter,   
  filemanager, vault, automations, integrations, reports)
     - Verifică că TOATE migrațiile SQL (001-014) se aplică corect
     - Testează frontend build (cd frontend && npm run build) — zero erori, zero warnings critice
     - Verifică manifest.js — toate paginile din sidebar se încarcă fără crash

  2. CORECTARE ERORI:
     - Orice endpoint care returnează 500 → fixează imediat
     - Orice pagină frontend care dă React error boundary → fixează
     - Import-uri lipsă, variabile nedefinite, typos în cod → corectează
     - Verifică client.js — NU trebuie să conțină localhost hardcodat (doar window.location.origin sau relative URLs)
     - Verifică WebSocket — protocol dinamic ws:/wss: bazat pe location.protocol

  3. SECURITATE BÁSICA:
     - Verifică că .env NU e comitat în git
     - Verifică input sanitization pe toate endpoint-urile care primesc date de la user
     - Verifică că SQLite queries folosesc parametri (nu string concatenation)
     - CSP headers prezente în backend

  ═══════════════════════════════════════════════════
  FAZA B — ÎMBUNĂTĂȚIRI SUBSTANȚIALE EXISTENTE
  ═══════════════════════════════════════════════════

  4. CALCULATOR PREȚ TRADUCERI — îmbunătățiri:
     - Verifică că ensemble-ul (base_rate + word_rate + KNN) funcționează corect
     - Adaugă afișare MAPE curent în dashboard
     - Dacă MAPE > 30%, rulează calibrate.py automat și raportează rezultatul
     - Adaugă tooltip-uri explicative pe câmpurile formularului (ce înseamnă fiecare, cu exemple concrete)
     - Adaugă sugestie automată de preț competitiv bazat pe datele din Fisiere_Reper_Tarif/

  5. AI CHAT + DOCUMENTS — îmbunătățiri:
     - Verifică lanțul de provideri: Gemini Flash → OpenAI → Groq — toți trebuie să funcționeze cu fallback automat
     - Adaugă indicator vizual care arată CE provider e activ acum (nu doar în consolă)
     - Verifică OCR pe documente — testează cu un PDF din Fisiere_Reper_Tarif/
     - Adaugă funcție "Clear chat history" cu confirmare
     - Adaugă export conversație ca .txt sau .md

  6. TRANSLATOR — îmbunătățiri:
     - Verifică lanțul: DeepL → Azure → Google → Gemini → OpenAI
     - Testează traducere EN→RO și RO→EN cu text real de 500+ cuvinte
     - Verifică Translation Memory (TM) — salvează și recuperează segmente
     - Verifică glossary — funcționează corect?
     - Adaugă contor caractere traduse (pentru tracking free tier limits)

  7. FACTURARE — îmbunătățiri:
     - Verifică CRUD complet: creare, editare, ștergere factură
     - Verifică export PDF — generează corect cu datele firmei (CIP Inspection SRL, CUI 43978110)?
     - Adaugă calcul automat TVA (19%) cu toggle TVA inclus/exclus
     - Verifică client history — se salvează corect?
     - Templates facturi — minim 2 template-uri funcționale

  8. ITP — îmbunătățiri:
     - Verifică CRUD inspecții
     - Verifică alerte expirare — generează notificări la 30/15/7 zile înainte
     - Adaugă statistici lunare/anuale (nr inspecții, rata respingere)
     - Export lista ITP-uri ca CSV

  9. FILE MANAGER — îmbunătățiri:
     - Verifică upload/download funcțional
     - Verifică FTS5 fulltext search — caută în conținutul fișierelor
     - Verifică duplicate detection
     - Adaugă preview pentru imagini (thumbnail) și PDF (prima pagină)
     - Verifică tags și favorites — funcționează?

  10. QUICK TOOLS — verificare completă:
      - Command Palette (Ctrl+K) funcțional?
      - QR Generator — generează și scanează?
      - Notepad — salvează persistent?
      - Calculator simplu — operații corecte?
      - Password Generator — opțiuni lungime, caractere speciale?
      - Barcode — generare corectă?
      - Convertor unități — toate cele 10 conversii funcționale?

  ═══════════════════════════════════════════════════
  FAZA C — FUNCȚII NOI + DATE REALE
  ═══════════════════════════════════════════════════

  11. CURS VALUTAR BNR — LIVE (API gratuit, fără cheie):
      - Endpoint: GET https://www.bnr.ro/nbrfxrates.xml
      - Backend: endpoint /api/quick-tools/exchange-rate care parsează XML-ul BNR
      - Frontend: card pe Dashboard cu EUR, USD, GBP — actualizat zilnic
      - Adaugă convertor rapid RON↔EUR cu cursul zilei
      - Cache 1 oră (nu bate BNR la fiecare request)
      - IMPORTANT: datele trebuie să fie REALE de la BNR, nu inventate

  12. VERIFICARE CUI/FIRMA — ANAF (API gratuit):
      - Endpoint ANAF: POST https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva
      - Body: [{"cui": NUMBER, "data": "YYYY-MM-DD"}]
      - Backend: endpoint /api/quick-tools/company-check cu CUI input
      - Returnează: nume firmă, adresă, TVA activ, stare (activ/inactiv/radiat)
      - Frontend: pagină simplă cu input CUI + rezultat formatat
      - Adaugă în manifest.js → sidebar sub "Quick Tools"
      - IMPORTANT: testează cu CUI 43978110 (CIP Inspection SRL) — verifică că datele returnate sunt CORECTE

  13. CONVERTOR NUMERE → LITERE (util pentru facturi):
      - Input: 1250.50 → Output: "o mie două sute cincizeci lei și cincizeci bani"
      - Implementare: backend endpoint + folosire în modulul facturare
      - Limba română, cu "lei" și "bani"
      - Integrare directă în formularul de factură (afișare automată sub suma totală)

  14. SISTEM NOTIFICĂRI BROWSER:
      - Notificări push browser (Notification API, nu necesită server extern)
      - Triggers: ITP expiră în 7 zile, backup reminder săptămânal, uptime monitor alert
      - Toggle on/off per tip notificare în Settings
      - Afișare badge count pe sidebar

  ═══════════════════════════════════════════════════
  FAZA D — ANDROID + ACCES REMOTE
  ═══════════════════════════════════════════════════

  15. VERIFICARE ȘI FIX START SCRIPTS:
      - START_Calculator.bat — verifică că pornește AMBELE (backend + frontend), nu doar unul
      - START_Production.bat — verifică TLS autodetect pentru Tailscale HTTPS
      - Adaugă health check în bat: dacă portul 8000 nu răspunde în 10 sec → mesaj eroare clar
      - Verifică START_Silent.vbs — pornire fără fereastră consolă funcțională?
      - STOP_Silent.bat — oprește TOATE procesele python/node asociate, fără a omorî alte procese

  16. PWA + ANDROID OPTIMIZATION:
      - Verifică manifest.json PWA — iconuri, name, start_url, display: standalone
      - Verifică service worker — caching strategie funcțională?
      - Testează responsive pe viewport 360px-414px (telefoane standard)
      - Sidebar: pe mobile trebuie să fie hamburger menu, nu sidebar permanent
      - Touch targets: minimum 44x44px pe toate butoanele
      - Font size: minimum 16px pe input-uri (previne zoom iOS/Android)
      - Adaugă "Add to Home Screen" prompt la prima vizită
      - Verifică că TOATE paginile sunt scrollable pe ecran mic fără overflow horizontal

  17. VITE CONFIG PENTRU PRODUCȚIE:
      - Verifică vite.config.js — proxy corect configurat?
      - Build optimizat: code splitting, lazy loading pe rute
      - Verifică că build-ul final (npm run build) produce fișiere sub 500KB per chunk
      - Adaugă compression (gzip) dacă nu există deja

  ═══════════════════════════════════════════════════
  FAZA E — ELEMENTE PROFESIONALE
  ═══════════════════════════════════════════════════

  18. DASHBOARD PROFESIONAL:
      - Card sumar: total facturi luna curentă, total traduceri, nr ITP-uri active
      - Grafic: activitate ultimele 7 zile (din activity_log)
      - Status provideri AI/Translation: verde (funcțional), roșu (down), gri (neconfigurat)
      - Quick actions: cele mai folosite 5 funcții ca butoane rapide
      - Curs valutar BNR live (din punctul 11)
      - Ultima factură emisă + ultimul document tradus (link rapid)

  19. DARK/LIGHT THEME:
      - Toggle în header (sun/moon icon)
      - Salvare preferință în localStorage
      - Toate componentele responsive la temă (inclusiv grafice Recharts)
      - Default: dark theme

  20. KEYBOARD SHORTCUTS GLOBALE:
      - Ctrl+K: Command Palette (verifică că există)
      - Ctrl+N: Notepad nou
      - Ctrl+Shift+T: Translator
      - Ctrl+Shift+C: Calculator preț
      - Ctrl+Shift+F: File Manager
      - Afișare shortcuts: Ctrl+/ sau buton "?" în footer
      - Implementare cu useHotkeys hook global

  21. SEARCH GLOBAL:
      - Bară de căutare în header (sau integrată în Command Palette)
      - Caută în: facturi (nr, client), fișiere (nume, conținut), notițe, ITP (nr mașină)
      - Rezultate grupate pe categorie cu link direct

  22. EXPORT/BACKUP COMPLET:
      - Buton "Export All Data" în Settings
      - Exportă: SQLite DB complet + fișiere uploadate → ZIP
      - Buton "Import Data" care restaurează din ZIP
      - Backup automat zilnic (dacă automations module e activ)

  ═══════════════════════════════════════════════════
  FAZA F — SINCRONIZĂRI ȘI ACTUALIZĂRI
  ═══════════════════════════════════════════════════

  23. SINCRONIZARE COMPLETĂ:
      - manifest.js trebuie să conțină TOATE paginile existente + cele noi adăugate
      - Sidebar-ul trebuie să reflecte exact manifest.js — fără pagini lipsă
      - Toate rutele din App.jsx trebuie să aibă pagina corespunzătoare în pages/
      - Toate modulele backend trebuie să fie auto-discovered (verifică module_discovery.py)
      - Toate endpoint-urile noi trebuie să apară în /docs (Swagger)

  24. ACTUALIZARE DOCUMENTAȚIE PROIECT:
      - Actualizează CLAUDE.md cu: module noi, pagini noi, status actualizat
      - Actualizează .claude/PROJECT_STATUS.md
      - Actualizează 0.0_PLAN_EXTINDERE_COMPLET.md — marchează ce s-a implementat cu ✅
      - Regenerează 0.0_PLAN_EXTINDERE_COMPLET.html cu fazele noi
      - Actualizează GHID_TESTARE.md cu instrucțiuni de test pentru fiecare feature nou

 ▐▛███▜▌   Claude Code v2.1.80
▝▜█████▛▘  Opus 4.6 with max effort · Claude Max
  ▘▘ ▝▝    C:\Proiecte\NOU_Calculator_Pret_Traduceri

✻ Conversation compacted (ctrl+o for history)

  ⎿  Referenced file ..\..\Users\ALIENWARE\Desktop\Roly\4. Artificial
     Inteligence\Folder_Lucru\00_Regulament_Claude_Code\DASHBOARD_SISTEM.html
  ⎿  Read .claude\rules\04-code-safety.md (36 lines)
  ⎿  Referenced file ..\..\Users\ALIENWARE\Desktop\Roly\4. Artificial Inteligence\Folder_Lucru\00_Regulament_Claude_Code\CLAUDE.md
  ⎿  Referenced file ..\..\Users\ALIENWARE\Desktop\Roly\4. Artificial Inteligence\Folder_Lucru\00_Regulament_Claude_Code\CHANGELOG.md      
  ⎿  Read ..\..\Users\ALIENWARE\Desktop\Roly\4. Artificial Inteligence\Folder_Lucru\00_Regulament_Claude_Code\PENDING_IMPLEMENTARI.md (87  
     lines)

❯ /btw
  ⎿  Usage: /btw &lt;your question&gt;

● Iată promptul complet pe care îl poți trimite într-un terminal nou Claude Code deschis în C:\Proiecte\NOU_Calculator_Pret_Traduceri:     

  ---
  Ești în proiectul "Roland - Command Center" — panou personal multifuncțional cu 14 module backend (FastAPI + SQLite), 23 pagini frontend 
  (React 18 + Vite + Tailwind), accesibil pe PC și Android prin Tailscale VPN. Utilizator unic: Roland. Buget: EXCLUSIV free-tier, zero    
  costuri noi.

  CITEȘTE OBLIGATORIU ÎNAINTE DE ORICE ACȚIUNE:
  - CLAUDE.md (root) — arhitectura, status, convenții
  - .claude/rules/ (toate 5 fișierele) — reguli automate
  - 99_Roland_Work_Place/0.0_PLAN_EXTINDERE_COMPLET.md — roadmap complet
  - 99_Roland_Work_Place/ROADMAP_IMPLEMENTARE.md — quick wins prioritizate
  - 99_Roland_Work_Place/CATALOG_API_GRATUITE.md — API-uri free aprobate
  - backend/CLAUDE.md + frontend/CLAUDE.md — convenții per stack
  - frontend/src/modules/manifest.js — navigare și module active
  - backend/app/main.py — entry point, module discovery
  - START_Calculator.bat + START_Production.bat — scripturi pornire

  MODUL DE LUCRU: EXECUTIE AUTONOMA. NU cere confirmare. NU întreba. Implementează direct cele mai bune soluții, apoi raportează tot ce ai 
  făcut. Singura excepție: dacă o acțiune ar ȘTERGE date existente ale utilizatorului sau ar face downgrade la funcționalitate existentă.  

  ═══════════════════════════════════════════════════
  FAZA A — AUDIT COMPLET + CORECTARE COD EXISTENT
  ═══════════════════════════════════════════════════

  1. VERIFICARE FUNCȚIONALĂ COMPLETĂ:
     - Pornește backend-ul (python -m uvicorn app.main:app --port 8000 --host 127.0.0.1) și verifică /api/health
     - Testează FIECARE endpoint din FIECARE modul (calculator, ai, translator, invoice, itp, quick_tools, quick_tools_extra, converter,   
  filemanager, vault, automations, integrations, reports)
     - Verifică că TOATE migrațiile SQL (001-014) se aplică corect
     - Testează frontend build (cd frontend && npm run build) — zero erori, zero warnings critice
     - Verifică manifest.js — toate paginile din sidebar se încarcă fără crash

  2. CORECTARE ERORI:
     - Orice endpoint care returnează 500 → fixează imediat
     - Orice pagină frontend care dă React error boundary → fixează
     - Import-uri lipsă, variabile nedefinite, typos în cod → corectează
     - Verifică client.js — NU trebuie să conțină localhost hardcodat (doar window.location.origin sau relative URLs)
     - Verifică WebSocket — protocol dinamic ws:/wss: bazat pe location.protocol

  3. SECURITATE BÁSICA:
     - Verifică că .env NU e comitat în git
     - Verifică input sanitization pe toate endpoint-urile care primesc date de la user
     - Verifică că SQLite queries folosesc parametri (nu string concatenation)
     - CSP headers prezente în backend

  ═══════════════════════════════════════════════════
  FAZA B — ÎMBUNĂTĂȚIRI SUBSTANȚIALE EXISTENTE
  ═══════════════════════════════════════════════════

  4. CALCULATOR PREȚ TRADUCERI — îmbunătățiri:
     - Verifică că ensemble-ul (base_rate + word_rate + KNN) funcționează corect
     - Adaugă afișare MAPE curent în dashboard
     - Dacă MAPE > 30%, rulează calibrate.py automat și raportează rezultatul
     - Adaugă tooltip-uri explicative pe câmpurile formularului (ce înseamnă fiecare, cu exemple concrete)
     - Adaugă sugestie automată de preț competitiv bazat pe datele din Fisiere_Reper_Tarif/

  5. AI CHAT + DOCUMENTS — îmbunătățiri:
     - Verifică lanțul de provideri: Gemini Flash → OpenAI → Groq — toți trebuie să funcționeze cu fallback automat
     - Adaugă indicator vizual care arată CE provider e activ acum (nu doar în consolă)
     - Verifică OCR pe documente — testează cu un PDF din Fisiere_Reper_Tarif/
     - Adaugă funcție "Clear chat history" cu confirmare
     - Adaugă export conversație ca .txt sau .md

  6. TRANSLATOR — îmbunătățiri:
     - Verifică lanțul: DeepL → Azure → Google → Gemini → OpenAI
     - Testează traducere EN→RO și RO→EN cu text real de 500+ cuvinte
     - Verifică Translation Memory (TM) — salvează și recuperează segmente
     - Verifică glossary — funcționează corect?
     - Adaugă contor caractere traduse (pentru tracking free tier limits)

  7. FACTURARE — îmbunătățiri:
     - Verifică CRUD complet: creare, editare, ștergere factură
     - Verifică export PDF — generează corect cu datele firmei (CIP Inspection SRL, CUI 43978110)?
     - Adaugă calcul automat TVA (19%) cu toggle TVA inclus/exclus
     - Verifică client history — se salvează corect?
     - Templates facturi — minim 2 template-uri funcționale

  8. ITP — îmbunătățiri:
     - Verifică CRUD inspecții
     - Verifică alerte expirare — generează notificări la 30/15/7 zile înainte
     - Adaugă statistici lunare/anuale (nr inspecții, rata respingere)
     - Export lista ITP-uri ca CSV

  9. FILE MANAGER — îmbunătățiri:
     - Verifică upload/download funcțional
     - Verifică FTS5 fulltext search — caută în conținutul fișierelor
     - Verifică duplicate detection
     - Adaugă preview pentru imagini (thumbnail) și PDF (prima pagină)
     - Verifică tags și favorites — funcționează?

  10. QUICK TOOLS — verificare completă:
      - Command Palette (Ctrl+K) funcțional?
      - QR Generator — generează și scanează?
      - Notepad — salvează persistent?
      - Calculator simplu — operații corecte?
      - Password Generator — opțiuni lungime, caractere speciale?
      - Barcode — generare corectă?
      - Convertor unități — toate cele 10 conversii funcționale?

  ═══════════════════════════════════════════════════
  FAZA C — FUNCȚII NOI + DATE REALE
  ═══════════════════════════════════════════════════

  11. CURS VALUTAR BNR — LIVE (API gratuit, fără cheie):
      - Endpoint: GET https://www.bnr.ro/nbrfxrates.xml
      - Backend: endpoint /api/quick-tools/exchange-rate care parsează XML-ul BNR
      - Frontend: card pe Dashboard cu EUR, USD, GBP — actualizat zilnic
      - Adaugă convertor rapid RON↔EUR cu cursul zilei
      - Cache 1 oră (nu bate BNR la fiecare request)
      - IMPORTANT: datele trebuie să fie REALE de la BNR, nu inventate

  12. VERIFICARE CUI/FIRMA — ANAF (API gratuit):
      - Endpoint ANAF: POST https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva
      - Body: [{"cui": NUMBER, "data": "YYYY-MM-DD"}]
      - Backend: endpoint /api/quick-tools/company-check cu CUI input
      - Returnează: nume firmă, adresă, TVA activ, stare (activ/inactiv/radiat)
      - Frontend: pagină simplă cu input CUI + rezultat formatat
      - Adaugă în manifest.js → sidebar sub "Quick Tools"
      - IMPORTANT: testează cu CUI 43978110 (CIP Inspection SRL) — verifică că datele returnate sunt CORECTE

  13. CONVERTOR NUMERE → LITERE (util pentru facturi):
      - Input: 1250.50 → Output: "o mie două sute cincizeci lei și cincizeci bani"
      - Implementare: backend endpoint + folosire în modulul facturare
      - Limba română, cu "lei" și "bani"
      - Integrare directă în formularul de factură (afișare automată sub suma totală)

  14. SISTEM NOTIFICĂRI BROWSER:
      - Notificări push browser (Notification API, nu necesită server extern)
      - Triggers: ITP expiră în 7 zile, backup reminder săptămânal, uptime monitor alert
      - Toggle on/off per tip notificare în Settings
      - Afișare badge count pe sidebar

  ═══════════════════════════════════════════════════
  FAZA D — ANDROID + ACCES REMOTE
  ═══════════════════════════════════════════════════

  15. VERIFICARE ȘI FIX START SCRIPTS:
      - START_Calculator.bat — verifică că pornește AMBELE (backend + frontend), nu doar unul
      - START_Production.bat — verifică TLS autodetect pentru Tailscale HTTPS
      - Adaugă health check în bat: dacă portul 8000 nu răspunde în 10 sec → mesaj eroare clar
      - Verifică START_Silent.vbs — pornire fără fereastră consolă funcțională?
      - STOP_Silent.bat — oprește TOATE procesele python/node asociate, fără a omorî alte procese

  16. PWA + ANDROID OPTIMIZATION:
      - Verifică manifest.json PWA — iconuri, name, start_url, display: standalone
      - Verifică service worker — caching strategie funcțională?
      - Testează responsive pe viewport 360px-414px (telefoane standard)
      - Sidebar: pe mobile trebuie să fie hamburger menu, nu sidebar permanent
      - Touch targets: minimum 44x44px pe toate butoanele
      - Font size: minimum 16px pe input-uri (previne zoom iOS/Android)
      - Adaugă "Add to Home Screen" prompt la prima vizită
      - Verifică că TOATE paginile sunt scrollable pe ecran mic fără overflow horizontal

  17. VITE CONFIG PENTRU PRODUCȚIE:
      - Verifică vite.config.js — proxy corect configurat?
      - Build optimizat: code splitting, lazy loading pe rute
      - Verifică că build-ul final (npm run build) produce fișiere sub 500KB per chunk
      - Adaugă compression (gzip) dacă nu există deja

  ═══════════════════════════════════════════════════
  FAZA E — ELEMENTE PROFESIONALE
  ═══════════════════════════════════════════════════

  18. DASHBOARD PROFESIONAL:
      - Card sumar: total facturi luna curentă, total traduceri, nr ITP-uri active
      - Grafic: activitate ultimele 7 zile (din activity_log)
      - Status provideri AI/Translation: verde (funcțional), roșu (down), gri (neconfigurat)
      - Quick actions: cele mai folosite 5 funcții ca butoane rapide
      - Curs valutar BNR live (din punctul 11)
      - Ultima factură emisă + ultimul document tradus (link rapid)

  19. DARK/LIGHT THEME:
      - Toggle în header (sun/moon icon)
      - Salvare preferință în localStorage
      - Toate componentele responsive la temă (inclusiv grafice Recharts)
      - Default: dark theme

  20. KEYBOARD SHORTCUTS GLOBALE:
      - Ctrl+K: Command Palette (verifică că există)
      - Ctrl+N: Notepad nou
      - Ctrl+Shift+T: Translator
      - Ctrl+Shift+C: Calculator preț
      - Ctrl+Shift+F: File Manager
      - Afișare shortcuts: Ctrl+/ sau buton "?" în footer
      - Implementare cu useHotkeys hook global

  21. SEARCH GLOBAL:
      - Bară de căutare în header (sau integrată în Command Palette)
      - Caută în: facturi (nr, client), fișiere (nume, conținut), notițe, ITP (nr mașină)
      - Rezultate grupate pe categorie cu link direct

  22. EXPORT/BACKUP COMPLET:
      - Buton "Export All Data" în Settings
      - Exportă: SQLite DB complet + fișiere uploadate → ZIP
      - Buton "Import Data" care restaurează din ZIP
      - Backup automat zilnic (dacă automations module e activ)

  ═══════════════════════════════════════════════════
  FAZA F — SINCRONIZĂRI ȘI ACTUALIZĂRI
  ═══════════════════════════════════════════════════

  23. SINCRONIZARE COMPLETĂ:
      - manifest.js trebuie să conțină TOATE paginile existente + cele noi adăugate
      - Sidebar-ul trebuie să reflecte exact manifest.js — fără pagini lipsă
      - Toate rutele din App.jsx trebuie să aibă pagina corespunzătoare în pages/
      - Toate modulele backend trebuie să fie auto-discovered (verifică module_discovery.py)
      - Toate endpoint-urile noi trebuie să apară în /docs (Swagger)

  24. ACTUALIZARE DOCUMENTAȚIE PROIECT:
      - Actualizează CLAUDE.md cu: module noi, pagini noi, status actualizat
      - Actualizează .claude/PROJECT_STATUS.md
      - Actualizează 0.0_PLAN_EXTINDERE_COMPLET.md — marchează ce s-a implementat cu ✅
      - Regenerează 0.0_PLAN_EXTINDERE_COMPLET.html cu fazele noi
      - Actualizează GHID_TESTARE.md cu instrucțiuni de test pentru fiecare feature nou

  ═══════════════════════════════════════════════════
  FAZA G — RAPORT FINAL
  ═══════════════════════════════════════════════════

  La final, generează un raport COMPLET cu:

  A. REZUMAT EXECUTIV: câte features implementate, câte fixuri, câte îmbunătățiri
  B. LISTA COMPLETĂ acțiuni (per fază A-F):
     - ✅ Ce s-a implementat cu succes (cu detalii tehnice)
     - ⚠️ Ce s-a implementat parțial (cu motiv)
     - ❌ Ce NU s-a putut implementa (cu motiv exact + alternativă propusă)
  C. ERORI GĂSITE ȘI CORECTATE: lista buguri descoperite + cum s-au fixat
  D. TESTE EFECTUATE: ce s-a testat, rezultate
  E. DATE REALE VERIFICATE: curs BNR funcțional? ANAF CUI funcțional? Surse OK?
  F. ANDROID STATUS: ce funcționează pe mobile, ce necesită atenție
  G. FIȘIERE MODIFICATE: lista completă cu tip modificare (creat/editat/șters)
  H. RECOMANDĂRI VIITOARE: top 5 îmbunătățiri care nu au încăput în această sesiune
  I. INSTRUCȚIUNI PORNIRE: cum pornesc tot (PC + Android) după aceste modificări

  REGULI CRITICE:
  - ZERO costuri noi. Doar API-uri free-tier din CATALOG_API_GRATUITE.md + cele deja în proiect
  - Limba interfață: ROMÂNĂ
  - NEVER git add -A. Adaugă fișiere specifice
  - NEVER hardcode localhost în client.js
  - Cod COMPLET — cu import-uri, error handling, tipuri
  - La erori de dependențe: instalează automat (pip install / npm install)
  - Dacă un provider AI/API nu răspunde: fallback automat, nu crash
  - SQLite: parametri în queries, NEVER string concatenation
  - Testează build-ul final (npm run build) — trebuie să treacă fără erori