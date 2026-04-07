"""
RIS — Setup Windows Service via WinSW.
Descarca WinSW de pe GitHub, configureaza si instaleaza serviciul RIS-Backend.
Ruleaza via SETUP_SERVICE.bat (necesita drepturi administrator).
"""
import ctypes
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# ── Configurare ──────────────────────────────────────────────────────────────
WINSW_GITHUB_API = "https://api.github.com/repos/winsw/winsw/releases/latest"
SERVICE_NAME = "RIS-Backend"
SERVICE_DISPLAY = "RIS Backend - Roland Intelligence System"
SERVICE_DESCRIPTION = "Backend FastAPI pentru Roland Intelligence System. Serveste API REST si frontend PWA pe portul 8001."
PROJECT_DIR = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_DIR / "tools"
WINSW_EXE = TOOLS_DIR / "RIS-Backend.exe"
WINSW_XML = TOOLS_DIR / "RIS-Backend.xml"
LOG_DIR = PROJECT_DIR / "logs"


def check_admin():
    """Verifica drepturi administrator."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_python_path():
    """Returneaza calea catre python.exe activ."""
    return sys.executable


def download_winsw():
    """Descarca WinSW de pe GitHub daca nu exista deja."""
    if WINSW_EXE.exists():
        print(f"[OK] WinSW exista deja: {WINSW_EXE}")
        return True

    print("[INFO] Descarcare WinSW de pe GitHub...")
    try:
        # Obtine URL download din GitHub API
        req = urllib.request.Request(
            WINSW_GITHUB_API,
            headers={"User-Agent": "RIS-Setup/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        tag = data.get("tag_name", "?")
        assets = [
            a for a in data.get("assets", [])
            if "x64" in a["name"] and a["name"].endswith(".exe")
        ]
        if not assets:
            print("[EROARE] Nu s-a gasit asset WinSW-x64.exe in release GitHub!")
            return False

        download_url = assets[0]["browser_download_url"]
        print(f"[INFO] Versiune: {tag}")
        print(f"[INFO] URL: {download_url}")

        # Descarca direct in tools/RIS-Backend.exe
        TOOLS_DIR.mkdir(exist_ok=True)
        urllib.request.urlretrieve(download_url, str(WINSW_EXE))
        print(f"[OK] WinSW descarcat: {WINSW_EXE} ({WINSW_EXE.stat().st_size // 1024} KB)")
        return True

    except Exception as e:
        print(f"[EROARE] Download WinSW esuat: {e}")
        return False


def create_winsw_config(python_path: str):
    """Creeaza fisierul XML de configurare WinSW."""
    LOG_DIR.mkdir(exist_ok=True)

    config = f"""<service>
  <id>{SERVICE_NAME}</id>
  <name>{SERVICE_DISPLAY}</name>
  <description>{SERVICE_DESCRIPTION}</description>

  <executable>{python_path}</executable>
  <arguments>-m backend.main</arguments>
  <workingdirectory>{PROJECT_DIR}</workingdirectory>

  <env name="RIS_ENV" value="production"/>
  <env name="PYTHONUNBUFFERED" value="1"/>

  <startmode>Automatic</startmode>
  <delayedAutoStart>false</delayedAutoStart>

  <logmode>rotate</logmode>
  <log mode="roll-by-size">
    <sizeThreshold>5120</sizeThreshold>
    <keepFiles>7</keepFiles>
  </log>
  <logpath>{LOG_DIR}</logpath>
  <outfile>{LOG_DIR}\\ris_service_stdout.log</outfile>
  <errfile>{LOG_DIR}\\ris_service_stderr.log</errfile>

  <onfailure action="restart" delay="3 sec"/>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="none"/>
  <resetfailure>1 hour</resetfailure>
</service>"""

    with open(WINSW_XML, "w", encoding="utf-8") as f:
        f.write(config)
    print(f"[OK] Configuratie WinSW scrisa: {WINSW_XML}")


def run_cmd(args, check=True):
    """Executa o comanda si afiseaza output-ul."""
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if check and result.returncode not in (0, 1):
        pass  # WinSW returneaza 1 pt uninstall daca nu exista
    return result


def uninstall_existing():
    """Dezinstaleaza serviciul existent daca ruleaza."""
    print("[INFO] Verificare serviciu existent...")
    result = subprocess.run(
        ["sc", "query", SERVICE_NAME],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[INFO] Serviciu existent gasit — oprire si dezinstalare...")
        subprocess.run(["sc", "stop", SERVICE_NAME], capture_output=True)
        time.sleep(3)
        run_cmd([str(WINSW_EXE), "uninstall"], check=False)
        time.sleep(2)
    else:
        print("[INFO] Niciun serviciu existent.")


def install_and_start():
    """Instaleaza si porneste serviciul via WinSW."""
    print("[INFO] Instalare serviciu...")
    result = run_cmd([str(WINSW_EXE), "install"])

    if result.returncode != 0 and "already" not in (result.stderr + result.stdout).lower():
        print(f"[EROARE] Instalare esuata (exit code {result.returncode})")
        return False

    print("[INFO] Pornire serviciu...")
    run_cmd([str(WINSW_EXE), "start"])
    time.sleep(3)

    # Verifica status
    status = subprocess.run(
        ["sc", "query", SERVICE_NAME],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if "RUNNING" in status.stdout:
        return True
    if "START_PENDING" in status.stdout:
        print("[INFO] Serviciu in pornire, asteptare 5 secunde...")
        time.sleep(5)
        status = subprocess.run(
            ["sc", "query", SERVICE_NAME],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return "RUNNING" in status.stdout

    return False


def get_tailscale_ip():
    """Obtine IP-ul Tailscale daca e instalat."""
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def main():
    print()
    print("  RIS - Roland Intelligence System")
    print("  Setup Windows Service (WinSW)")
    print("  ==================================")
    print()

    # Verifica admin
    if not check_admin():
        print("[EROARE] Rulati ca Administrator!")
        print("         Click dreapta pe SETUP_SERVICE.bat -> Run as administrator")
        sys.exit(1)

    python_path = get_python_path()
    print(f"[OK] Python: {python_path}")
    print(f"[OK] Proiect: {PROJECT_DIR}")

    # 1. Descarca WinSW
    if not download_winsw():
        sys.exit(1)

    # 2. Creeaza configuratia XML
    create_winsw_config(python_path)

    # 3. Dezinstaleaza serviciu vechi (daca exista)
    uninstall_existing()

    # 4. Instaleaza si porneste
    ok = install_and_start()

    print()
    if ok:
        tailscale_ip = get_tailscale_ip()
        print("  ================================================")
        print("  [OK] Serviciu RIS-Backend PORNIT cu succes!")
        print()
        print("  Acces local:     http://localhost:8001")
        if tailscale_ip:
            print(f"  Acces Tailscale: http://{tailscale_ip}:8001")
        else:
            print("  Acces Tailscale: http://[IP-Tailscale]:8001")
            print("  (obtine IP cu: tailscale ip -4)")
        print()
        print("  Comenzi rapide:")
        print("    MANAGE_SERVICE.bat start|stop|restart|status")
        print("  ================================================")
    else:
        print("[ATENTIE] Serviciul nu e RUNNING.")
        print("          Verifica: logs\\ris_service_stderr.log")
        sc_out = subprocess.run(
            ["sc", "query", SERVICE_NAME],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        print(sc_out.stdout)

    print()
    input("Apasa Enter pentru a inchide...")


if __name__ == "__main__":
    main()
