"""
render_job_map.py — Harta pasilor per provider dintr-un job RIS.

Parseaza logs/job_{id}.log (produs de backend/services/job_logger.py) si genereaza
o pagina HTML lizibila (self-contained, fara JS, se deschide direct in browser) care
arata EXACT ce a facut fiecare provider/sursa:
  - fiecare sursa externa (ANAF, SEAP, Portal Just, ...): OK/FAIL, durata, campuri extrase
  - fiecare sectiune de raport: CE provider AI a scris-o (claude/groq/...), fallback sau nu,
    cate cuvinte, cat a durat
  - rezumatul final: completeness, scor risc, formate generate, timp total

Uz:
    python tools/render_job_map.py <job_id>
    python tools/render_job_map.py            # ultimul job log modificat

Iesire: outputs/<job_id>/execution_map.html  (+ un rezumat text in consola)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"

# --- regex pe formatul din job_logger.py ---
RE_HDR = re.compile(r"JOB START:\s*(\S+)")
RE_KV = re.compile(r"\|\s+(Analysis|CUI|Company|Time):\s*(.*)$")
RE_AGENT = re.compile(r"AGENT_([A-Z]+)\s*\|\s*(START|END)(?:\s*\|\s*(.*))?$")
RE_SOURCE = re.compile(
    r"SOURCE\s*\|\s*(.+?)\s*\|\s*(OK|FAIL)\s*\|\s*(\d+)ms\s*\|\s*(.*)$"
)
RE_SYN = re.compile(
    r"SYNTHESIS\s*\|\s*(.+?)\s*\|\s*provider=(\S+?)(\s*\(FALLBACK\))?\s*\|\s*(OK|FAIL)\s*\|\s*(\d+)\s*words\s*\|\s*(\d+)ms"
)
RE_COMPL = re.compile(r"COMPLETENESS\s*\|\s*score=(\d+)%\s*\|\s*quality=(\S+)\s*\|\s*(\d+)/(\d+)")
RE_REPORT = re.compile(r"REPORT_GEN\s*\|\s*formats=(.*?)\s*\|\s*(\d+)ms")
RE_SUM = re.compile(r"\|\s+(Status|Total time|Sources OK|Sources FAIL|Completeness|Risk score|Report formats):\s*(.*)$")

# Provider AI -> eticheta lizibila
PROVIDER_LABEL = {
    "claude": "Claude Opus (Max)", "groq": "Groq (Llama 4 Scout)",
    "gemini": "Gemini 2.5 Flash", "mistral": "Mistral Small 3",
    "cerebras": "Cerebras (gpt-oss-120b)", "degraded": "Fallback determinist (fara AI)",
    "unknown": "necunoscut",
}


def parse_log(text: str) -> dict:
    meta = {"job_id": "", "analysis": "", "cui": "", "company": "", "time": ""}
    sources, synth, summary = [], [], {}
    completeness = None
    formats = None
    for line in text.splitlines():
        m = RE_HDR.search(line)
        if m:
            meta["job_id"] = m.group(1)
        m = RE_KV.search(line)
        if m:
            k = m.group(1).lower().replace(" ", "_")
            meta[k] = m.group(2).strip()
        m = RE_SOURCE.search(line)
        if m:
            sources.append({
                "name": m.group(1).strip(), "status": m.group(2),
                "ms": int(m.group(3)), "detail": m.group(4).strip(),
            })
            continue
        m = RE_SYN.search(line)
        if m:
            synth.append({
                "section": m.group(1).strip(), "provider": m.group(2).strip(),
                "fallback": bool(m.group(3)), "status": m.group(4),
                "words": int(m.group(5)), "ms": int(m.group(6)),
            })
            continue
        m = RE_COMPL.search(line)
        if m:
            completeness = {"score": int(m.group(1)), "quality": m.group(2),
                            "passed": int(m.group(3)), "total": int(m.group(4))}
        m = RE_REPORT.search(line)
        if m:
            formats = m.group(1).strip()
        m = RE_SUM.search(line)
        if m:
            summary[m.group(1).strip()] = m.group(2).strip()
    return {"meta": meta, "sources": sources, "synth": synth,
            "completeness": completeness, "formats": formats, "summary": summary}


def _fmt_ms(ms: int) -> str:
    return f"{ms/1000:.1f}s" if ms >= 1000 else f"{ms}ms"


def render_html(data: dict) -> str:
    meta = data["meta"]
    e = html.escape
    rows_src = ""
    for s in data["sources"]:
        cls = "ok" if s["status"] == "OK" else "fail"
        rows_src += (
            f"<tr class='{cls}'><td>{e(s['name'])}</td><td class='st'>{s['status']}</td>"
            f"<td class='num'>{_fmt_ms(s['ms'])}</td><td>{e(s['detail'])}</td></tr>"
        )
    rows_syn = ""
    for s in data["synth"]:
        prov = s["provider"]
        is_claude = prov == "claude"
        cls = "claude" if is_claude else ("degraded" if prov == "degraded" else "fb" if s["fallback"] else "other")
        badge = "SCRIS DE CLAUDE" if is_claude else ("FALLBACK" if s["fallback"] else "")
        label = PROVIDER_LABEL.get(prov, prov)
        rows_syn += (
            f"<tr class='{cls}'><td>{e(s['section'])}</td>"
            f"<td class='prov'>{e(label)} <span class='b'>{badge}</span></td>"
            f"<td class='num'>{s['words']}w</td><td class='num'>{_fmt_ms(s['ms'])}</td></tr>"
        )
    claude_cnt = sum(1 for s in data["synth"] if s["provider"] == "claude")
    total_syn = len(data["synth"])
    compl = data["completeness"] or {}
    summary = data["summary"]
    formats = data["formats"] or summary.get("Report formats", "—")
    verdict = (
        f"Claude Opus a scris {claude_cnt}/{total_syn} sectiuni"
        if claude_cnt else "Claude Opus NU a scris nicio sectiune (toate pe fallback)"
    )
    vcls = "vok" if claude_cnt else "vbad"

    return f"""<!doctype html><html lang=ro><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Harta executie — {e(meta.get('company') or meta.get('cui') or meta['job_id'])}</title>
<style>
:root{{color-scheme:dark}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#12121f;color:#e8e8f0;margin:0;padding:24px;line-height:1.5}}
.wrap{{max-width:1000px;margin:0 auto}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;color:#a9a9c8;margin:26px 0 10px;border-bottom:1px solid #2a2a44;padding-bottom:6px}}
.meta{{color:#9a9ac0;font-size:13px;margin-bottom:8px}}
.verdict{{padding:12px 16px;border-radius:8px;font-weight:600;margin:14px 0}}
.vok{{background:#12331f;border:1px solid #2a7a45;color:#7fe0a0}}
.vbad{{background:#3a1a1a;border:1px solid #7a2a2a;color:#f0a0a0}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px}}
td,th{{padding:7px 10px;text-align:left;border-bottom:1px solid #22223a;vertical-align:top}}
th{{color:#8a8ab0;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.num{{text-align:right;white-space:nowrap;color:#b8b8d8;font-variant-numeric:tabular-nums}}
.st{{font-weight:600}}
tr.ok .st{{color:#6fd08a}} tr.fail .st{{color:#e88}} tr.fail td{{color:#c99}}
tr.claude{{background:#0f2a18}} tr.claude .prov{{color:#7fe0a0;font-weight:600}}
tr.fb .prov,tr.degraded .prov{{color:#e0b060}}
.prov .b{{font-size:10px;padding:2px 6px;border-radius:4px;margin-left:6px;background:#2a7a45;color:#dfffe8}}
tr.fb .prov .b,tr.degraded .prov .b{{background:#7a5a2a;color:#ffe8c0}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0}}
.card{{background:#1a1a2e;border:1px solid #2a2a44;border-radius:8px;padding:10px 14px;font-size:13px;min-width:120px}}
.card b{{display:block;font-size:18px;color:#fff}}
.legend{{font-size:12px;color:#8a8ab0;margin-top:6px}}
</style></head><body><div class=wrap>
<h1>Harta executiei — pasii exacti per provider</h1>
<div class=meta>{e(meta.get('company',''))} &middot; CUI {e(meta.get('cui',''))} &middot; {e(meta.get('analysis',''))} &middot; {e(meta.get('time',''))}<br>Job: {e(meta['job_id'])}</div>
<div class="verdict {vcls}">{e(verdict)}</div>
<div class=cards>
<div class=card>Scor risc<b>{e(summary.get('Risk score','—'))}</b></div>
<div class=card>Completitudine<b>{compl.get('score','—')}%</b></div>
<div class=card>Timp total<b>{e(summary.get('Total time','—'))}</b></div>
<div class=card>Surse OK<b>{e(summary.get('Sources OK','—'))}</b></div>
<div class=card>Formate<b style="font-size:13px">{e(formats)}</b></div>
</div>
<h2>1. Surse de date interogate (Agenti 1-4)</h2>
<table><tr><th>Sursa / Provider</th><th>Status</th><th>Durata</th><th>Ce a returnat</th></tr>{rows_src}</table>
<h2>2. Sinteza raportului — cine a scris fiecare sectiune (Agent 5)</h2>
<table><tr><th>Sectiune</th><th>Provider AI</th><th>Cuvinte</th><th>Durata</th></tr>{rows_syn}</table>
<div class=legend>Verde = scris de Claude Opus. Portocaliu = fallback (alt provider a preluat).
Durata sectiunii = TOTAL pe cascada, atribuit castigatorului (ex. Claude 250s + fallback instant apare pe castigator).</div>
</div></body></html>"""


def main():
    if len(sys.argv) > 1:
        job_id = sys.argv[1].replace("job_", "").replace(".log", "")
        log_path = LOGS / f"job_{job_id}.log"
    else:
        logs = sorted(LOGS.glob("job_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not logs:
            print("Niciun job_*.log gasit in logs/")
            return 1
        log_path = logs[0]
        job_id = log_path.stem.replace("job_", "")

    if not log_path.exists():
        print(f"Nu exista: {log_path}")
        return 1

    data = parse_log(log_path.read_text(encoding="utf-8", errors="replace"))
    out_dir = ROOT / "outputs" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "execution_map.html"
    out_html.write_text(render_html(data), encoding="utf-8")

    # Rezumat text in consola
    claude_cnt = sum(1 for s in data["synth"] if s["provider"] == "claude")
    print(f"Job: {job_id} | {data['meta'].get('company','')} ({data['meta'].get('cui','')})")
    print(f"Surse: {sum(1 for s in data['sources'] if s['status']=='OK')} OK / "
          f"{sum(1 for s in data['sources'] if s['status']=='FAIL')} FAIL")
    print(f"Sinteza: {claude_cnt}/{len(data['synth'])} sectiuni scrise de CLAUDE")
    for s in data["synth"]:
        fb = " (FALLBACK)" if s["fallback"] else ""
        print(f"   - {s['section']:<22} provider={s['provider']}{fb} | {s['words']}w | {_fmt_ms(s['ms'])}")
    print(f"Formate: {data['formats'] or data['summary'].get('Report formats','—')}")
    print(f"\nHarta HTML: {out_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
