' RIS — Roland Intelligence System
' Dublu-click: rebuild frontend + restart serviciu + deschide browser.
' Fara ferestre de terminal. Functioneaza si prin Tailscale (telefon/tableta).
'
' Ce face:
'   1. Build frontend (npm run build) — aplica modificari UI
'   2. Stop + Start serviciu RIS-Backend — aplica modificari backend
'   3. Deschide http://localhost:8001 in browser
'   4. Afiseaza IP Tailscale pentru acces de pe telefon

Dim oShell, oFSO, oSvc, colItems, objItem, sState
Dim sProjectDir, sFrontendDir, sDistDir, sTailscaleIP

Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

sProjectDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
sFrontendDir = sProjectDir & "\frontend"
sDistDir = sFrontendDir & "\dist"

' ── 1. BUILD FRONTEND (silent, fara fereastra) ────────────────────────
' Ruleaza npm run build doar daca folderul frontend exista
If oFSO.FolderExists(sFrontendDir) Then
    ' Ruleaza build in background (0 = hidden window), asteapta sa termine (True)
    Dim sBuildCmd
    sBuildCmd = "cmd /c cd /d """ & sFrontendDir & """ && npm run build > """ & sProjectDir & "\logs\ris_frontend_build.log"" 2>&1"
    oShell.Run sBuildCmd, 0, True
End If

' ── 2. RESTART SERVICIU (stop + start) ────────────────────────────────
On Error Resume Next
Set oSvc = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
Set colItems = oSvc.ExecQuery("SELECT State FROM Win32_Service WHERE Name='RIS-Backend'")

sState = "NotFound"
For Each objItem In colItems
    sState = objItem.State
Next
On Error GoTo 0

If sState = "Running" Then
    ' Serviciul ruleaza — restart (stop + start)
    oShell.Run "sc stop RIS-Backend", 0, True
    WScript.Sleep 3000
    oShell.Run "sc start RIS-Backend", 0, False
    WScript.Sleep 3000
ElseIf sState = "Stopped" Then
    ' Serviciul oprit — doar start
    oShell.Run "sc start RIS-Backend", 0, False
    WScript.Sleep 3000
ElseIf sState = "NotFound" Then
    ' Serviciul nu e instalat — incearca pornire directa
    Dim sDirectCmd
    sDirectCmd = "cmd /c cd /d """ & sProjectDir & """ && python -m backend.main"
    oShell.Run sDirectCmd, 0, False
    WScript.Sleep 4000
End If

' ── 3. DETECTEAZA IP TAILSCALE ────────────────────────────────────────
sTailscaleIP = ""
On Error Resume Next
Dim oExec, sLine
Set oExec = oShell.Exec("cmd /c tailscale ip -4 2>nul")
If Not oExec Is Nothing Then
    Do While Not oExec.StdOut.AtEndOfStream
        sLine = Trim(oExec.StdOut.ReadLine)
        If Left(sLine, 4) = "100." Then
            sTailscaleIP = sLine
        End If
    Loop
End If
On Error GoTo 0

' ── 4. DESCHIDE BROWSER ──────────────────────────────────────────────
oShell.Run "http://localhost:8001", 1, False

' ── 5. NOTIFICARE (optional — cu IP Tailscale) ──────────────────────
Dim sMsg
sMsg = "RIS pornit!" & vbCrLf & vbCrLf
sMsg = sMsg & "Local:  http://localhost:8001" & vbCrLf

If sTailscaleIP <> "" Then
    sMsg = sMsg & "Telefon: http://" & sTailscaleIP & ":8001" & vbCrLf
    sMsg = sMsg & vbCrLf & "Deschide linkul de sus pe telefon (prin Tailscale)."
Else
    sMsg = sMsg & "Tailscale: nedetectat (instaleaza pentru acces de pe telefon)"
End If

MsgBox sMsg, vbInformation, "Roland Intelligence System"
