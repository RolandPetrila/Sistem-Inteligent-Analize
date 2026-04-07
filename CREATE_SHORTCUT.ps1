# CREATE_SHORTCUT.ps1 - Creeaza shortcut RIS pe Desktop
# Rulare: PowerShell -ExecutionPolicy Bypass -File CREATE_SHORTCUT.ps1

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "RIS.lnk"
$IconPath = Join-Path $ProjectDir "ris_icon.ico"
$TargetUrl = "http://localhost:8001"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "rundll32.exe"
$Shortcut.Arguments = "url.dll,FileProtocolHandler $TargetUrl"
$Shortcut.Description = "Roland Intelligence System - Business Intelligence"
$Shortcut.WorkingDirectory = $ProjectDir
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()

Write-Host "[OK] Shortcut creat: $ShortcutPath"
Write-Host "     Tinta: $TargetUrl"
if (Test-Path $IconPath) {
    Write-Host "     Iconita: $IconPath"
} else {
    Write-Host "[ATENTIE] ris_icon.ico nu exista - ruleaza: python tools/create_icon.py"
}
