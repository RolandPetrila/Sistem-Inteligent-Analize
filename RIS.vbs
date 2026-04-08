' RIS — Roland Intelligence System
' Dublu-click: porneste serviciul (daca e oprit) si deschide browser.
' Fara ferestre de terminal. Fara interactiune necesara.

Dim oShell, oSvc, colItems, objItem, sState

Set oShell = CreateObject("WScript.Shell")

' ── Verifica starea serviciului RIS-Backend ──────────────────────────────
On Error Resume Next
Set oSvc = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
Set colItems = oSvc.ExecQuery("SELECT State FROM Win32_Service WHERE Name='RIS-Backend'")

sState = "NotFound"
For Each objItem In colItems
    sState = objItem.State
Next
On Error GoTo 0

' ── Porneste serviciul daca nu ruleaza ──────────────────────────────────
If sState = "Stopped" Then
    oShell.Run "sc start RIS-Backend", 0, False
    WScript.Sleep 3500
ElseIf sState = "NotFound" Then
    ' Serviciul nu e instalat — afiseaza mesaj minimal
    MsgBox "Serviciul RIS-Backend nu este instalat." & vbCrLf & _
           "Ruleaza tools\setup_service.py ca administrator.", _
           vbExclamation, "RIS — Serviciu lipsa"
    WScript.Quit
End If

' ── Deschide interfata in browser default ─────────────────────────────
oShell.Run "http://localhost:8001", 1, False
