# RIS — Pornire, NSSM Service & Tailscale Mobile

## Arhitectura de pornire (post-NSSM)

```
Windows Service "RIS-Backend"
  └── uvicorn backend.main:app --host 0.0.0.0 --port 8001
       ├── Serveste API-ul REST (toate endpoint-urile /api/)
       ├── Serveste frontend-ul static din frontend/dist/
       └── Expus pe Tailscale IP:8001 pentru telefon
```

Un singur serviciu. Fără ferestre. Pornit automat la boot Windows.

---

## Comenzi rapide NSSM

```bat
REM Pornire serviciu
sc start RIS-Backend

REM Oprire serviciu
sc stop RIS-Backend

REM Status serviciu
sc query RIS-Backend

REM Restart complet
sc stop RIS-Backend && sc start RIS-Backend

REM Din NSSM direct
tools\nssm.exe start RIS-Backend
tools\nssm.exe stop RIS-Backend
tools\nssm.exe restart RIS-Backend
tools\nssm.exe status RIS-Backend
```

---

## Acces de pe telefon prin Tailscale

### Cerințe

1. Tailscale instalat și conectat pe laptop
2. Tailscale instalat și conectat pe telefon (același cont)
3. Serviciul RIS-Backend pornit

### Găsește IP-ul Tailscale al laptopului

```bat
tailscale ip -4
REM Exemplu rezultat: 100.64.X.X
```

### Accesează din browser pe telefon

```
http://100.64.X.X:8001
```

### Instalare PWA pe telefon (Add to Home Screen)

1. Deschide Chrome/Safari pe telefon
2. Navighează la `http://100.64.X.X:8001`
3. Meniu browser → "Add to Home Screen" / "Instalează aplicația"
4. Confirmă → iconița RIS apare pe ecranul de start al telefonului
5. La tap pe iconița RIS → deschide direct interfața (fără bara de browser)

---

## Rebuild frontend (necesar după modificări UI)

```bat
cd C:\Proiecte\Sistem_Inteligent_Analize\frontend
npm run build
REM Fișierele din dist/ sunt servite automat de backend
REM Nu e nevoie de restart serviciu
```

---

## Actualizare IP Tailscale în .env (dacă e cazul)

Dacă aplicația folosește variabile cu IP-ul Tailscale:

```
TAILSCALE_IP=100.64.X.X
```

Obține IP-ul cu: `tailscale ip -4`

---

## Iconița de pe desktop

Shortcut-ul `RIS.lnk` de pe desktop folosește iconița `ris_icon.ico` din folderul proiectului.

- **Dublu-click** pe shortcut → deschide `http://localhost:8001` în browser (serviciul e deja pornit)
- Iconița PWA de pe telefon → deschide `http://100.64.X.X:8001`

---

## Troubleshooting

### Serviciul nu pornește

```bat
REM Verifică log-ul serviciului
type logs\ris_runtime.log | tail -50
REM Sau Event Viewer → Windows Logs → Application → sursa "RIS-Backend"
```

### Backend pornit dar UI nu se afișează

```bat
REM Verifică că dist/ există și e up-to-date
dir frontend\dist\index.html
REM Dacă lipsește: rebuild
cd frontend && npm run build && cd ..
```

### Telefonul nu poate accesa

1. Verifică că Tailscale e conectat pe ambele dispozitive: `tailscale status`
2. Verifică că portul 8001 nu e blocat de Windows Firewall
3. Testează din browser laptop: `http://100.64.X.X:8001` (cu propriul IP)

### Schimbi ceva în cod → restart serviciu

```bat
sc stop RIS-Backend
REM Fă modificările
sc start RIS-Backend
```

---

## Fișiere relevante post-cleanup

| Fișier                 | Rol                                  |
| ---------------------- | ------------------------------------ |
| `tools\nssm.exe`       | Manager serviciu Windows             |
| `ris_icon.ico`         | Iconița aplicației (desktop + PWA)   |
| `RIS.lnk`              | Shortcut desktop cu iconița RIS      |
| `RIS_TEST.bat`         | Rulare suite teste (pytest + vitest) |
| `frontend\dist\`       | Frontend compilat servit de backend  |
| `logs\ris_runtime.log` | Log-uri backend                      |

**Fișiere eliminate:** START_RIS.vbs, STOP_RIS.vbs, START_RIS_silent.bat, STOP_RIS_silent.bat, START_RIS_TAILSCALE.bat
