#!/usr/bin/env python3
"""tools/ris-analyze.py — CLI wrapper pentru RIS API local.

Exemplu:
    python tools/ris-analyze.py --cui 26313362 --type FULL_COMPANY_PROFILE --level 2
    python tools/ris-analyze.py --cui 26313362 --output json
    python tools/ris-analyze.py --cui 26313362 --api-key mykey --base-url http://localhost:8001
"""
import argparse
import json
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("Eroare: httpx nu e instalat. Ruleaza: pip install httpx", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="RIS Analyze CLI — analiza firma din terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--cui", required=True, help="CUI firma (ex: 26313362)")
    parser.add_argument(
        "--type", default="FULL_COMPANY_PROFILE",
        choices=[
            "FULL_COMPANY_PROFILE", "COMPETITION_ANALYSIS", "PARTNER_RISK_ASSESSMENT",
            "MARKET_OPPORTUNITY", "DUE_DILIGENCE",
        ],
        help="Tipul analizei (default: FULL_COMPANY_PROFILE)",
    )
    parser.add_argument("--level", type=int, default=2, choices=[1, 2, 3],
                        help="Nivelul raportului: 1=Rapid, 2=Standard, 3=Detaliat (default: 2)")
    parser.add_argument("--base-url", default="http://localhost:8001",
                        help="URL-ul backend-ului RIS (default: http://localhost:8001)")
    parser.add_argument("--api-key", default=os.getenv("RIS_API_KEY", ""),
                        help="API key (sau setati variabila RIS_API_KEY in mediu)")
    parser.add_argument("--output", default="summary", choices=["json", "summary"],
                        help="Format output: summary (default) sau json complet")
    args = parser.parse_args()

    headers: dict = {}
    if args.api_key:
        headers["X-RIS-Key"] = args.api_key

    base = args.base_url.rstrip("/")

    with httpx.Client(timeout=30) as client:
        # 1. Creeaza job
        print(f"[RIS] Creare job pentru CUI {args.cui}...", file=sys.stderr)
        try:
            r = client.post(
                f"{base}/api/jobs",
                json={
                    "analysis_type": args.type,
                    "report_level": args.level,
                    "input_params": {"cui": args.cui},
                },
                headers=headers,
            )
            r.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"[EROARE] Nu s-a putut crea job-ul: {exc}", file=sys.stderr)
            sys.exit(1)

        job_id = r.json()["id"]
        print(f"[RIS] Job creat: {job_id}", file=sys.stderr)

        # 2. Porneste job
        try:
            client.post(f"{base}/api/jobs/{job_id}/start", headers=headers)
        except httpx.HTTPError as exc:
            print(f"[EROARE] Nu s-a putut porni job-ul: {exc}", file=sys.stderr)
            sys.exit(1)

        # 3. Poll status pana la finalizare
        print("[RIS] Astept finalizarea analizei...", file=sys.stderr)
        data: dict = {}
        while True:
            time.sleep(5)
            try:
                status_r = client.get(f"{base}/api/jobs/{job_id}", headers=headers)
                data = status_r.json()
            except httpx.HTTPError as exc:
                print(f"[AVERTISMENT] Eroare poll status: {exc}", file=sys.stderr)
                continue

            pct = data.get("progress_percent", 0)
            status = data.get("status", "UNKNOWN")
            step = data.get("current_step", "")
            print(f"  [{status}] {pct}% — {step}", file=sys.stderr)
            if status in ("DONE", "FAILED", "PAUSED"):
                break

    if data.get("status") == "DONE":
        if args.output == "summary":
            try:
                reports_r = httpx.get(
                    f"{base}/api/reports",
                    params={"limit": 1, "job_id": job_id},
                    headers=headers,
                    timeout=10,
                )
                reports = reports_r.json().get("reports", [])
            except httpx.HTTPError:
                reports = []

            if reports:
                r0 = reports[0]
                print(f"\nCompanie : {r0.get('title', 'N/A')}")
                print(f"Risc     : {r0.get('risk_score', '?')}")
                print(f"Scor     : {r0.get('numeric_score', '?')}/100")
                summary_text = str(r0.get("summary", ""))[:300]
                if summary_text:
                    print(f"Rezumat  : {summary_text}")
                formats = r0.get("formats_available", [])
                if formats:
                    print(f"Formate  : {', '.join(formats)}")
            else:
                print("[INFO] Analiza finalizata dar nu s-au gasit rapoarte.", file=sys.stderr)
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        err_msg = data.get("error_message", "eroare necunoscuta")
        print(f"[EROARE] Job {data.get('status', 'ESUAT')}: {err_msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
