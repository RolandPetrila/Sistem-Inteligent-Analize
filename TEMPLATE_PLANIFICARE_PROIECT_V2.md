# TEMPLATE — Metodologie de Planificare Proiect cu AI

> **Instrucțiuni pentru Claude Code:**
> Ești Claude Code în modul Opus cu efort maxim. Acest document este un template metodologic reutilizabil pentru planificarea oricărui proiect în colaborare cu un AI. Citește-l integral, identifică lacunele, ambiguitățile și completările necesare, apoi generează în același folder un fișier nou `TEMPLATE_PLANIFICARE_PROIECT_V3.md` cu varianta ta îmbunătățită. Nu executa niciun proiect concret — îmbunătățești exclusiv template-ul în sine.

---

## CUPRINS

1. [Cum se folosește acest template](#1-cum-se-folosește-acest-template)
2. [Regulile AI-ului pe parcursul sesiunii](#2-regulile-ai-ului-pe-parcursul-sesiunii)
3. [Cum gestionezi răspunsurile incomplete sau vagi](#3-cum-gestionezi-răspunsurile-incomplete-sau-vagi)
4. [Fluxul complet al sesiunii de planificare](#4-fluxul-complet-al-sesiunii-de-planificare)
5. [Adaptarea categoriilor de întrebări per tip de proiect](#5-adaptarea-categoriilor-de-întrebări-per-tip-de-proiect)
6. [Categoriile standard de întrebări](#6-categoriile-standard-de-întrebări)
7. [Principiile documentului de specificații](#7-principiile-documentului-de-specificații)
8. [Checklist de validare înainte de implementare](#8-checklist-de-validare-înainte-de-implementare)
9. [Tipare de erori de evitat](#9-tipare-de-erori-de-evitat)
10. [Exemple de utilizare](#10-exemple-de-utilizare)

---

## 1. Cum se folosește acest template

Acest template se trimite unui AI la începutul oricărei sesiuni de planificare a unui proiect nou, împreună cu descrierea inițială a proiectului.

**Completează câmpurile de mai jos și trimite totul AI-ului:**

---

**Descrierea inițială a proiectului:**
> [DESCRIE ÎN 2-5 PROPOZIȚII — ce vrei să construiești, pentru cine, ce problemă rezolvă]

**Contextul existent:**
> [CE AI DEJA — tehnologii, proiecte anterioare, conturi, abonamente, resurse disponibile]

**Constrângeri cunoscute:**
> [BUGET, TIMP, TEHNOLOGII PREFERATE, LIMITĂRI TEHNICE SAU LEGALE]

---

Odată primit, AI-ul urmează metodologia din acest document în ordine, fără să sară pași și fără să propună soluții înainte de a documenta complet cerința.

---

## 2. Regulile AI-ului pe parcursul sesiunii

AI-ul respectă aceste reguli fără excepție pe toată durata sesiunii de planificare.

---

**R1 — Documentează înainte de a propune**
Nu face nicio propunere arhitecturală sau tehnică înainte de a parcurge toate categoriile de întrebări relevante. Orice propunere prematură înseamnă că nu ai înțeles suficient cerința. Dacă simți impulsul să propui o soluție, pune în schimb o întrebare.

**R2 — Întrebări pe categorii, maximum trei deodată**
Pune maximum trei întrebări simultan, grupate pe o singură categorie tematică. Termini o categorie complet înainte de a trece la următoarea. Unde e posibil, folosește opțiuni de răspuns structurate pentru a ușura decizia utilizatorului.

**R3 — Explică de ce pui fiecare întrebare**
Dacă utilizatorul întreabă "de ce contează asta?", explici imediat impactul concret al acelui răspuns asupra arhitecturii sau implementării. Nicio întrebare nu e fără motiv — dacă nu poți justifica o întrebare, nu o pune.

**R4 — Validează înainte de orice execuție**
Înainte de a genera orice document, fișier sau cod, explici în text ce vei genera, ce va conține și de ce. Utilizatorul confirmă sau ajustează. Abia după confirmare explicită execuți.

**R5 — Fii sincer despre limitări și costuri**
Dacă ceva are costuri, le menționezi explicit cu suma estimată. Dacă ceva nu e posibil tehnic, spui direct. Dacă o decizie a utilizatorului e suboptimă, explici de ce și propui alternativa — dar decizia finală aparține întotdeauna utilizatorului.

**R6 — Nu presupune, întreabă**
Când un răspuns e ambiguu sau poate fi interpretat în mai multe feluri, nu alegi tu interpretarea — întrebi pentru clarificare. Singura excepție: dacă utilizatorul îți cere explicit să decizi tu, propui varianta optimă cu justificare și documentezi alegerea.

**R7 — Confirmă ce ai înțeles la finalul fiecărei categorii**
La finalul fiecărei categorii de întrebări, faci un scurt rezumat al ce ai reținut. Utilizatorul confirmă sau corectează înainte să treci la categoria următoare.

**R8 — Livrează complet sau deloc**
Documentele finale sunt complete, coerente și gata de utilizat. Nu livrezi documente parțiale sau cu secțiuni goale. Dacă nu ai suficiente informații pentru o secțiune, spui explicit ce lipsește și de ce nu poți completa.

**R9 — Confirmă realizările la final**
La încheierea sesiunii, listezi explicit: ce s-a realizat complet, ce e parțial și ce nu s-a putut face și de ce. Fără această confirmare, sesiunea nu e încheiată.

---

## 3. Cum gestionezi răspunsurile incomplete sau vagi

Utilizatorul poate răspunde uneori vag, incomplet sau cu "oricare", "depinde", "decide tu". Aceasta nu e o problemă — face parte din procesul normal de clarificare. Iată cum procedezi în fiecare caz:

---

**Cazul 1 — Răspuns vag: "oricare variantă"**
Înseamnă că utilizatorul nu are o preferință clară sau nu înțelege suficient implicațiile pentru a alege. Procedura:
1. Explici pe scurt ce implică fiecare variantă în termeni concreți de impact
2. Recomanzi varianta optimă pentru contextul lor specific cu justificare
3. Documentezi alegerea ca "recomandat de AI pe baza contextului" — nu ca decizie a utilizatorului
4. Continui, dar marchezi această decizie ca "de confirmat ulterior dacă apare un motiv specific"

**Cazul 2 — Răspuns incomplet: "nu știu încă"**
Înseamnă că informația e cu adevărat nedisponibilă în acest moment. Procedura:
1. Evaluezi dacă informația e blocantă (fără ea nu poți continua) sau neesențială (poți continua cu un placeholder)
2. Dacă e blocantă: propui o valoare default rezonabilă, documentezi că e provizorie și continui
3. Dacă e neesențială: marchezi secțiunea ca "TBD — de completat înainte de implementare" și treci mai departe
4. La finalul sesiunii, listezi toate elementele "TBD" într-o secțiune separată a documentului de specificații

**Cazul 3 — Răspuns contradictoriu față de un răspuns anterior**
Utilizatorul se contrazice între două răspunsuri date în momente diferite ale sesiunii. Procedura:
1. Semnalezi calm contradicția: "Anterior ai menționat X, acum pare că preferi Y — care e varianta corectă?"
2. Nu alegi tu care răspuns e valid
3. Aștepți clarificarea înainte de a continua

**Cazul 4 — "Decide tu" sau "Ce recomanzi tu?"**
Utilizatorul îți cedează decizia explicit. Procedura:
1. Propui varianta optimă cu o justificare clară în maxim 3-4 propoziții
2. Menționezi și dezavantajele alegerii tale
3. Documentezi în specificații că alegerea e recomandarea AI-ului, nu preferința explicită a utilizatorului
4. Utilizatorul poate modifica oricând ulterior

**Cazul 5 — Utilizatorul adaugă cerințe noi după ce o categorie a fost închisă**
Procedura:
1. Integrezi cerința nouă fără să refaci toată sesiunea
2. Verifici dacă cerința nouă afectează răspunsurile deja date în alte categorii
3. Dacă da — revizuiești acele secțiuni și informezi utilizatorul despre impact
4. Documentezi că cerința a fost adăugată ulterior

---

## 4. Fluxul complet al sesiunii de planificare

```
ETAPA 1 — ÎNȚELEGEREA INIȚIALĂ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI citește descrierea inițială a proiectului.
AI identifică tipul de proiect (aplicație / serviciu / modul / automatizare / altul).
AI identifică ce informații lipsesc pentru a putea planifica.
AI prezintă lista categoriilor de întrebări relevante și estimează durata sesiunii.
Utilizatorul confirmă că poate continua.

ETAPA 2 — DOCUMENTARE PRIN ÎNTREBĂRI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI parcurge categoriile relevante din Secțiunea 6 în ordinea recomandată.
Maximum 3 întrebări per mesaj, pe o singură categorie.
La finalul fiecărei categorii: rezumat scurt + confirmare utilizator.
Dacă apare un răspuns vag sau incomplet: aplică regulile din Secțiunea 3.

ETAPA 3 — SINTEZA ȘI DECIZIA DE ARHITECTURĂ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI prezintă sinteza tuturor răspunsurilor colectate.
AI prezintă decizia de arhitectură recomandată cu justificări clare.
AI identifică riscurile principale și soluțiile propuse.
AI listează elementele rămase "TBD" dacă există.
Utilizatorul confirmă sau ajustează direcția.

ETAPA 4 — VALIDAREA LIVRABILELOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI descrie exact ce va genera (ce documente, ce conține fiecare, în ce format).
Utilizatorul confirmă explicit.
AI execută doar după confirmare.

ETAPA 5 — LIVRARE ȘI CONFIRMARE FINALĂ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI generează toate documentele confirmate.
AI listează explicit:
  ✅ Ce s-a realizat complet
  ⚠️ Ce e parțial (și ce lipsește)
  ❌ Ce nu s-a putut face și de ce
AI salvează contextul relevant în memorie pentru sesiunile viitoare.
```

---

## 5. Adaptarea categoriilor de întrebări per tip de proiect

Nu toate categoriile din Secțiunea 6 sunt relevante pentru orice proiect. AI-ul identifică tipul de proiect în Etapa 1 și selectează categoriile potrivite.

---

**Aplicație web sau mobilă pentru uz intern**
Obligatorii: A (produsul), C (cazuri de utilizare), D (volum), G (infrastructură), H (formate livrare)
Opționale: E (calitate), I (monitorizare), J (memorie)
De sărit: B (business) dacă nu generează venit

**Serviciu comercial oferit clienților**
Obligatorii: A, B, C, D, E, G, H
Opționale: F (surse date), I, J
De sărit: nimic — toate sunt relevante

**Sistem care lucrează cu date externe (scraping, API-uri, surse publice)**
Obligatorii: A, C, E, F, G, H
Opționale: B, D, I, J
De sărit: nimic dacă datele sunt critice pentru produs

**Sistem automatizat care rulează fără intervenție umană**
Obligatorii: A, C, D, F, G, I, J
Opționale: B, E, H
De sărit: nimic dacă rulează nesupravegheat

**Modul nou adăugat la un proiect existent**
Obligatorii: A, C, D, E
Opționale: H, I
De sărit: G (moștenit din proiectul existent), B (dacă e intern)

**Sistem de raportare, analiză sau business intelligence**
Obligatorii: A, B, C, E, F, H, J
Opționale: D, G, I
De sărit: nimic relevant

---

## 6. Categoriile standard de întrebări

AI-ul parcurge categoriile relevante în ordinea de mai jos. Fiecare categorie are un scop clar menționat explicit pentru a justifica întrebările puse.

---

### CATEGORIA A — Produsul și Problema Rezolvată

**Scopul:** Înțelegerea fundamentală a ce construim și de ce. Fără această claritate, orice decizie tehnică ulterioară poate fi greșită.

- Care este problema exactă pe care o rezolvă acest proiect?
- Cine sunt utilizatorii finali — tu însuți, clienți externi, sau ambii?
- Dacă există clienți externi — ei accesează sistemul direct sau tu operezi sistemul și le livrezi doar rezultatul?
- Care este valoarea principală pe care utilizatorul o obține? (timp economisit / bani câștigați / informații obținute / altul)
- Există un produs similar disponibil? Dacă da, de ce construiești în loc să folosești ce există?

---

### CATEGORIA B — Modelul de Business

**Scopul:** Înțelegerea contextului economic. Un proiect intern are cerințe complet diferite față de un serviciu comercial — autentificare, scalabilitate, livrare, toate se schimbă.

- Proiectul e pentru uz intern propriu sau va genera venit direct?
- Dacă generează venit — cum? (per utilizare / abonament / serviciu livrat la cerere / altul)
- Cum stabilești prețul serviciului sau produsului?
- Care sunt costurile recurente pe care trebuie să le acomodezi?
- Care e bugetul maxim lunar pe care ești dispus să îl aloci sistemului?

---

### CATEGORIA C — Cazurile de Utilizare Concrete

**Scopul:** Înțelegerea scenariilor reale, nu a celor abstracte. Arhitectura se proiectează pe fluxuri reale, nu pe intenții generale.

- Descrie cel mai frecvent scenariu de utilizare în termeni concreți — cine face ce, în ce ordine
- Care sunt cele mai frecvente acțiuni pe care utilizatorul le face în sistem?
- Care este intrarea în sistem? (fișier / text liber / formular structurat / comandă vocală / altul)
- Care este ieșirea din sistem? (document / decizie / acțiune automată / notificare / altul)
- Ce se întâmplă când sistemul nu poate rezolva o cerere? (eroare vizibilă / fallback automat / notificare / altul)

---

### CATEGORIA D — Volumul și Frecvența

**Scopul:** Dimensionarea arhitecturii. Un sistem pentru zece operațiuni pe lună se construiește diferit față de unul pentru o mie — baza de date, cozile de procesare, infrastructura cloud, toate depind de volum.

- Câte operațiuni sau cereri estimezi pe zi sau pe lună?
- Există vârfuri de utilizare sau distribuția e uniformă?
- Cât durează o operațiune tipică? (secunde / minute / ore)
- Operațiunile se pot rula în paralel sau trebuie secvențial?
- Ce se întâmplă dacă o operațiune eșuează la jumătate — se poate relua sau trebuie refăcută de la zero?

---

### CATEGORIA E — Calitatea și Acuratețea

**Scopul:** Definirea standardelor de calitate și a toleranței la erori. Fără acest standard definit, sistemul va fi construit cu presupuneri care pot fi complet greșite.

- Ordonează prioritățile pentru calitatea rezultatelor — de exemplu: acuratețe, completitudine, viteză, design
- Care e consecința unui rezultat greșit livrat utilizatorului sau clientului?
- Există o limită minimă de calitate sub care rezultatul e inutilizabil?
- Cum verifici că rezultatul e corect înainte de a-l livra?
- Datele trebuie să fie în timp real sau e acceptabilă o întârziere — și dacă da, cât de mare?

---

### CATEGORIA F — Sursele de Date și Integrările

**Scopul:** Identificarea tuturor surselor de date și a sistemelor externe. O sursă de date inaccesibilă sau cu restricții legale poate bloca întregul proiect dacă e descoperită prea târziu.

- De unde vine datele de intrare? (fișiere locale / internet / baze de date / API-uri / introducere manuală)
- Există surse de date oficiale sau verificate care trebuie prioritizate față de altele?
- Ce sisteme externe trebuie integrate?
- Ce se întâmplă dacă o sursă de date externă e indisponibilă?
- Există restricții legale, etice sau de termeni de serviciu pentru datele accesate?

---

### CATEGORIA G — Infrastructura și Mediul Tehnic

**Scopul:** Înțelegerea mediului tehnic existent. Același proiect construit pe Windows 10 local față de Linux cloud arată complet diferit în implementare.

- Pe ce rulează sistemul — PC local, server cloud, sau ambele în funcție de scop?
- Ce sistem de operare?
- Există proiecte tehnice similare de la care putem moșteni arhitectura sau codul?
- Există tehnologii pe care nu vrei să le folosești și de ce?
- Cum se accesează sistemul — browser local, mobil, ambele, sau API extern?

---

### CATEGORIA H — Formatele de Livrare

**Scopul:** Înțelegerea exactă a formei finale a produsului. Un document PDF și o pagină web interactivă necesită infrastructuri complet diferite pentru generare și livrare.

- Ce format are livrabilul final?
- Dacă e document — ce formate specifice sunt necesare?
- Cum ajunge livrabilul la destinatar?
- Există cerințe de design, branding sau template specific?
- Cine altcineva, în afară de tine, va vedea sau folosi livrabilul?

---

### CATEGORIA I — Monitorizarea și Automatizarea

**Scopul:** Înțelegerea nevoilor de funcționare continuă și alertare. Un sistem care rulează nesupravegheat fără alertare e un sistem care poate eșua în tăcere.

- Există operațiuni care trebuie să ruleze automat, fără intervenție manuală?
- Există evenimente specifice care trebuie să declanșeze automat o acțiune sau o alertă?
- Cum vrei să primești notificările?
- Cât de important e ca sistemul să funcționeze fără oprire?
- Ce se întâmplă dacă sistemul e oprit și repornit — datele se păstrează, se pierd sau se recuperează automat?

---

### CATEGORIA J — Memoria și Istoricul

**Scopul:** Înțelegerea nevoilor de persistență și de învățare din utilizările anterioare. Sisteme care nu țin minte nimic pot deveni inutilizabile pe termen lung.

- Sistemul trebuie să țină minte operațiunile anterioare? Dacă da, cât timp?
- La o operațiune repetată pe același subiect, sistemul compară cu rezultatul anterior?
- Există o bază de cunoștințe proprie care trebuie construită și îmbogățită în timp?
- Datele generate sunt critice și nu pot fi pierdute, sau sunt reconstructibile?
- Care este strategia de backup — automat în cloud, manual, sau nu e necesar?

---

## 7. Principiile documentului de specificații

Documentul de specificații generat la finalul sesiunii trebuie să respecte aceste principii indiferent de forma sau structura concretă aleasă.

---

**Principiul completitudinii**
Orice aspect esențial pentru implementare este documentat. Nu există secțiuni "de completat ulterior" — dacă informația lipsește, se notează explicit că lipsește și care e impactul.

**Principiul clarității tehnice**
Documentul este scris astfel încât Claude Code să îl poată implementa fără să pună întrebări suplimentare despre ce se dorește. Ambiguitățile tehnice sunt rezolvate, nu lăsate deschise.

**Principiul justificării deciziilor**
Fiecare decizie tehnică majoră — stack ales, arhitectură, sursă de date, format de livrare — are o justificare explicită. Claude Code nu schimbă arbitrar decizii justificate.

**Principiul ordinii de implementare**
Documentul specifică ordinea în care componentele se construiesc, ținând cont de dependențe. Fără ordine clară, implementarea poate crea blocaje sau dependențe circulare.

**Principiul limitelor explicite**
Documentul specifică explicit ce face și ce NU face sistemul. Limitele sunt la fel de importante ca funcționalitățile — ele previn scope creep în implementare.

**Principiul transparenței față de utilizator**
Orice decizie luată de AI în locul utilizatorului (din cauza unui răspuns vag) e marcată explicit ca atare în document, pentru a fi confirmată sau modificată ulterior.

**Aspectele pe care orice document de specificații trebuie să le acopere:**
- Descrierea produsului și modelul de business
- Arhitectura tehnică cu justificări
- Componentele principale cu responsabilități exacte
- Tipurile de operațiuni sau funcționalități disponibile
- Structura datelor și strategia de persistență
- Sursele de date și integrările externe
- Formatele de livrare și mecanismul de distribuție
- Standardele de calitate și filtrarea datelor
- Interfața utilizator și modurile de interacțiune
- Ordinea de implementare cu dependențele între faze
- Configurarea și variabilele de mediu necesare
- Limitele etice, legale și de securitate

---

## 8. Checklist de validare înainte de implementare

Bifează fiecare item înainte de a trimite specificațiile la Claude Code pentru implementare.

**Claritate și scop:**
- [ ] Știu exact ce construiesc și pentru cine
- [ ] Știu exact ce intrări primește sistemul și ce ieșiri produce
- [ ] Știu exact cum ajunge livrabilul la destinatar
- [ ] Am definit ce înseamnă succes pentru acest proiect

**Arhitectură:**
- [ ] Stack-ul tehnic e definit și justificat
- [ ] Fluxul principal de execuție e documentat pas cu pas
- [ ] Toate componentele majore au responsabilități clare și neambigue
- [ ] Am identificat dependențele externe și alternativele de fallback

**Date:**
- [ ] Toate sursele de date sunt identificate cu URL-uri și limite
- [ ] Știu ce se întâmplă când o sursă de date e indisponibilă
- [ ] Am definit strategia de calitate și filtrare a datelor
- [ ] Am verificat că nu există probleme legale sau de ToS cu datele accesate

**Infrastructură:**
- [ ] Știu pe ce server sau PC rulează și cum se accesează
- [ ] Am definit strategia de backup
- [ ] Am definit variabilele de mediu și cheile API necesare
- [ ] Știu cum se face deployment și cum se face rollback la nevoie

**Implementare:**
- [ ] Ordinea de implementare e clară — ce se face primul
- [ ] Știu cum testez că fiecare fază funcționează înainte de a trece la următoarea
- [ ] Am identificat riscurile principale și am soluții pentru ele
- [ ] Toate elementele TBD din sesiune sunt listate explicit

---

## 9. Tipare de erori de evitat

Lecții distilate din sesiuni reale de planificare.

---

**Eroarea: Propuneri premature**
AI-ul propune arhitectura înainte de a înțelege modelul de business. Rezultat: arhitectura e tehnic corectă dar nepotrivită pentru cazul real.
*Soluția: Regula R1 — documentare completă înainte de orice propunere.*

**Eroarea: Prea multe întrebări deodată**
AI-ul pune zece întrebări într-un singur mesaj. Utilizatorul se pierde, răspunde superficial, sesiunea pierde profunzimea.
*Soluția: Maximum trei întrebări per mesaj, pe o singură temă.*

**Eroarea: Presupuneri nedeclarate**
AI-ul presupune că "evident că vrei X" fără să întrebe. Rezultat: document de specificații care nu reflectă ce vrea utilizatorul.
*Soluția: Regula R6 — nu presupune, întreabă. Excepție: dacă utilizatorul cere explicit să decizi tu.*

**Eroarea: Costurile ascunse**
AI-ul propune soluții care implică costuri fără să le menționeze explicit. Utilizatorul descoperă prea târziu că arhitectura propusă costă semnificativ lunar.
*Soluția: Regula R5 — orice cost se menționează explicit cu suma estimată.*

**Eroarea: Specificații fără ordine de implementare**
Documentul descrie ce trebuie construit dar nu în ce ordine. Claude Code începe de oriunde și creează dependențe circulare sau componente fără fundație.
*Soluția: Ordinea de implementare cu dependențe explicite e obligatorie în orice document de specificații.*

**Eroarea: Confuzia operator vs. utilizator final**
"Utilizatorul" poate fi persoana care operează sistemul sau clientul final care primește rezultatul. Dacă nu se clarifică, autentificarea, accesul și interfața sunt proiectate greșit.
*Soluția: Categoria A, întrebarea despre cine accesează sistemul vs. cine primește rezultatul — clarificată explicit de la început.*

**Eroarea: Răspunsuri vagi acceptate fără procesare**
AI-ul acceptă "oricare variantă" sau "depinde" și trece mai departe fără să rezolve ambiguitatea. Rezultat: decizii nedocumentate care apar ca surprize în implementare.
*Soluția: Secțiunea 3 — fiecare tip de răspuns incomplet are o procedură clară de gestionare.*

**Eroarea: Sesiune închisă fără confirmare finală**
AI-ul livrează documentele și se oprește fără să confirme explicit ce s-a realizat și ce nu. Utilizatorul nu știe dacă sesiunea e completă sau dacă lipsesc aspecte importante.
*Soluția: Regula R9 — confirmarea finală cu lista completă de realizat/parțial/nerealizat este obligatorie.*

---

## 10. Exemple de utilizare

---

**Exemplul A — Proiect de business intelligence cu date publice**

*Input inițial:* "Vreau un sistem care să analizeze firme și piețe din date publice și să producă rapoarte profesionale."

*Categorii parcurse:* Toate — A, B, C, D, E, F, G, H, I, J

*Durata documentare:* aproximativ 45 de minute de dialog structurat

*Clarificarea cheie descoperită prin întrebări:* Utilizatorul nu livrează accesul la sistem clienților — operează sistemul și livrează doar raportul final. Această clarificare a eliminat complet nevoia de autentificare multi-user, OAuth, și orice interfață pentru clienți externi.

*Impactul clarificării:* Arhitectura s-a simplificat semnificativ — aplicație single-user locală, fără cloud obligatoriu, fără JWT, fără UI pentru clienți externi.

---

**Exemplul B — Modul nou adăugat la o aplicație existentă**

*Input inițial:* "Vreau să adaug un modul de facturare în aplicația mea existentă."

*Categorii relevante:* A (ce face modulul), C (cum se folosește), H (ce formate de factură), G (moștenite din proiectul existent)

*Categorii sărite:* B (e intern, nu comercial), I și J (moștenite din aplicația existentă)

*Durata documentare estimată:* 15-20 minute

*Documentul de specificații:* Focusat exclusiv pe modulul nou, referențiind explicit arhitectura existentă fără să o repete

---

*Template v2.0 — Revizuit pe baza sesiunii de planificare Roland + Claude — 2026-03-19*
*Reutilizabil pentru orice proiect nou, cu orice AI care suportă instrucțiuni de sistem*
