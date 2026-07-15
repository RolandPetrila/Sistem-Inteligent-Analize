# Spike — sursa de cash-flow operational real (CFO)

> Verdict: **INCHIS. Nu exista.** Verificat empiric la sursa (API real + cadru legal), 2026-07-15.
> Scop: sa nu se re-cerceteze. Daca cineva propune din nou "hai sa luam CFO real", citeste asta intai.
> **ZERO cod scris pentru acest spike** — a fost pura decizie de investitie.

---

## Intrebarea

RIS foloseste azi `cash_flow_operational` **FABRICAT**: `cfo = profit_net * 1.1`, multiplicator
inventat (introdus in `4a05b5c`, 2026-04-07). Merita inlocuit cu o sursa reala?

Recomandarea initiala (Opus): _"o sursa CFO reala = cel mai mare ROI singular — deblocheaza
simultan TATA/Beneish, Piotroski F2/F3, si o parte din rate. 3 probleme, 1 cauza."_
**Aceasta recomandare s-a dovedit FALSA.** Vezi sectiunea 3.

## 1. ANAF Bilant NU expune CFO — si nici nu permite derivarea (empiric)

API-ul `GET https://webservicesp.anaf.ro/bilant?an={year}&cui={cui}` returneaza **exact 20 de
indicatori (I1-I20)**, IDENTICI indiferent de marimea firmei — verificat live pe cea mai mare
companie din tara si pe o firma mica: acelasi set.

- **(a) Direct:** zero indicatori de trezorerie. Fara cash-flow, fara incasari/plati.
- **(b) Derivat** (`CFO = Profit net + Amortizare - dWC`): imposibil. Din 5 componente necesare:
  - **Amortizarea lipseste complet** — niciun indicator din cele 20.
  - **`I7 "DATORII"` e agregat unic** — comercial + financiar, fara split de scadenta.
- **(c) Cuantificare** (criteriul Altman: eroarea vs latimea benzii de decizie):
  Beneish TATA are coeficientul **7.770** (cel mai greu din model), banda de decizie **0.44**.
  Doar lipsa amortizarii deplaseaza M-score cu 0.08-0.16 (firme non-capital-intensive) pana la
  **0.39-0.78** (capital-intensive). Agregarea DATORII adauga pana la **0.78-2.33** (2-5x banda).
  => nu e "estimare degradata", e aruncare de moneda. **INDISPONIBIL**, acelasi criteriu ca Altman.

**Efect colateral confirmat:** aceeasi dovada (`I7` agregat) **confirma la sursa** decizia D1/D2
(Altman INDISPONIBIL). Nu era doar credinta noastra — e limitare reala a datelor. CFO, TATA si
Altman X1 sunt blocate de **acelasi** blocaj unic, si cad impreuna. Coerent.

## 2. Nu exista sursa externa free — plafonul e LEGAL, nu tehnic

Situatia fluxurilor de trezorerie e obligatorie **doar pentru firme mijlocii/mari**
(OMFP 1802/2014: 2 din 3 praguri — active >17,5M lei, CA >35M lei, >=50 angajati). Micro-
intreprinderile nu o intocmesc deloc; la cele mici e optionala. IMM = ~99,8% din firmele active RO.

**Deci acoperirea maxima teoretica a ORICARUI fisier bulk (data.gov.ro / MFinante) e sub ~2%** —
plafonul e legal, deci niciun format de fisier si nicio sursa platita nu-l poate ridica. Datele
pur si simplu nu au fost niciodata depuse.

- **BVB** (firme listate, chiar au CFO complet IFRS): ~366 firme din ~1,4 mil active = **0,03%**.
- Termene.ro / OpenCorporates / OpenSanctions / D&B / IBISWorld: deja INCHISE (vezi memoria
  `project_ris_free_sources_decisions`, cercetate la sursa 2026-07-11). Nu re-cerceta.
- Fals-pozitiv de evitat: un document ANAF despre "Situatia fluxurilor de trezorerie cod 03/04"
  se refera la **SECTORUL PUBLIC** (ordonatori de credite, bugete locale), NU la societati
  comerciale. Verificat prin citirea directa a PDF-ului.

## 3. ROI-ul recomandarii initiale era EXAGERAT (verificat in cod)

Chiar daca ar fi existat o sursa CFO, cele "3 probleme" erau de fapt **una**:

| Consumator          | Afirmatia initiala | Realitatea verificata in cod                                                                                                                                                                                               |
| ------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Beneish M**       | "se deblocheaza"   | **FALS — ramane INDISPONIBIL.** Gate-ul (`predictive_models.py:389`) e `AND` intre CFO ("TATA") **SI** `cheltuieli_materiale` ("GMI") — a doua cheie, niciodata scrisa nicaieri in backend. CFO rezolva jumatate din gate. |
| **Piotroski F2/F3** | "se deblocheaza"   | **PARTIAL ADEVARAT.** Piotroski nu era blocat — producea deja valoare. CFO l-ar face mai _corect_, nu l-ar reinvia. Algebra confirmata (vezi 4).                                                                           |
| **Rate financiare** | "o parte din rate" | **FALS — ZERO.** Cele 6 rate randate (`scoring.py:181-235`: Marja Profit, ROE, ROA, Datorii/Capital, Rata Capitalizare, CA/Angajat) nu folosesc CFO deloc.                                                                 |

**Lectie:** afirmatia de ROI a fost facuta din memorie, fara sa fie verificata in cod. A costat
~10 minute de agenti sa fie demontata — ar fi costat zile de implementare daca o urmam.

## 4. Consecinta directa: Piotroski F2/F3 -> None (fix DEFINITIV, nu provizoriu)

Verificat algebric (`predictive_models.py:135-139`): cu `cfo = profit * 1.1`, criteriile
**F2** (`CFO > 0`) si **F3** (`CFO > profit net`) se reduc AMBELE la semnul lui `profit` —
identic cu **F1**. In cazul tipic (F5/F7 = None, confirmat pe 100% din rapoartele reale din
`data/ris.db`), disponibile = 7 criterii => **semnul profitului decide 3 din 7 puncte = 43%**.

Fiindca sectiunile 1+2 arata ca nu exista si nu va exista o sursa CFO free, F2/F3 -> `None` e
**fix definitiv**, nu carpeala temporara. Acelasi tratament ca F5/F7.

**Inconsecventa interna gasita:** gate-ul aplicat azi (`895fd82`) la F5/F7/Beneish **nu** a fost
aplicat si la F2/F3, desi au exact acelasi mod de esec (default fabricat -> punct fals).

**`cfo = profit_net * 1.1` se elimina, nu se eticheteaza "proxy".** O eticheta nu repara un numar
inventat care intra cu coeficient 7.770 intr-un model cu banda 0.44 — exact rationamentul aplicat
deja la D3 (Beneish nu mai acuza).

## 5. Descoperire colaterala P0 — orbire la pierderi (NU era scopul spike-ului)

Spike-ul a pornit de la intrebarea "de ce zice codul ca formatul difera intre firme mari si mici?".
Raspunsul: **nu difera** — comentariul (`anaf_bilant_client.py:87-88`) e fals. Tragand de fir:

ANAF trimite `I19` = **pierderea NETA**, cu denumire inconsecventa: la firmele mari vine
mislabelat `"Pierdere bruta"` (identic cu `I17`), la cele mici vine `"Pierdere  neta"` cu
**spatiu dublu**. Parserul RIS potriveste pe TEXT, deci ambele esueaza — prima suprascrie tacut
`pierdere_bruta`, a doua e aruncata tacut. `pierdere_neta` **nu e scrisa NICIODATA**, desi e
citita la `:208` ("fix-ul C1", care oricum se declanseaza doar `if val is None`, cand ANAF
trimite `0`).

**Efect:** o firma cu pierdere neta reala intra in RIS ca **`profit_net = 0`**. Verificat live pe
o companie de stat cu pierdere cronica (CUI 477647; cifrele nu se comit — repo PUBLIC).
**Zmijewski** (`:484`, coef -4.513 pe PN/TA, prag distres `x > 0`) iese subevaluat cu **+0.328**
pe acel caz — eroare **mereu optimista**, exact pe firmele riscante. Kill-switch-ul D1 (cuplat la
Zmijewski) e partial orb.

Latent pana acum fiindca toate cele 8 firme din `companies` sunt profitabile. **Aceeasi clasa:
"cod care citeste chei pe care nimic nu le scrie", tacut** — si nu era in niciun audit
(nici in cele 25 MEDIUM / 24 LOW din 07-13).

---

## Decizii propuse (Roland le poate veta)

- **D4 — CFO ramane INDISPONIBIL definitiv.** Nu exista sursa free+legala+cu acoperire IMM.
  Blocaj legal (<2%), nu tehnic. Nu re-cerceta fara dovada ca s-a schimbat OMFP 1802/2014.
- **D5 — Piotroski F2/F3 -> `None`**, ca F5/F7. `cfo = profit_net * 1.1` se elimina.
- **D6 — Beneish ramane INDISPONIBIL** si dupa D4/D5, dintr-un al doilea motiv independent:
  `cheltuieli_materiale` (GMI) nu e scrisa nicaieri.
- **P0 — orbirea la pierderi se repara** (bug pur, nu decizie de produs).
