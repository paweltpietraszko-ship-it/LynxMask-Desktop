' uruchom.vbs v1.4 — Pseudominizer
' v1.1 — widoczne okno CMD, logowanie do pseudominizer.log
' v1.2 — czyszczenie __pycache__ przed startem
' v1.3 — jawna ścieżka do Python 3.14 (pomija WindowsApps stub w PATH)
' v1.4 — [LYNX-SEC-DISK-PII] F3: log tylko w oknie konsoli (S5: logi bez zapisu na dysk);
'        stary pseudominizer.log usuwany przy starcie

Option Explicit

Dim objShell, objFSO
Dim strDir, strPython, strCmd, strLog, strCache

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

strDir   = objFSO.GetParentFolderName(WScript.ScriptFullName)
strLog   = strDir & "\pseudominizer.log"
strCache = strDir & "\__pycache__"

' Usun stary plik logu z wersji <= v1.3 (S5: logi nie trafiaja na dysk)
If objFSO.FileExists(strLog) Then
    objFSO.DeleteFile strLog, True
End If

' Wyczysc __pycache__ przed startem — zapobiega ladowaniu starego kodu
If objFSO.FolderExists(strCache) Then
    objFSO.DeleteFolder strCache, True
End If

' Szukaj Pythona — jawna ścieżka przed fallbackiem na PATH
' Kolejność: venv lokalny > Python 3.14 > py.exe > python.exe z PATH
strPython = ""
If objFSO.FileExists(strDir & "\venv\Scripts\python.exe") Then
    strPython = """" & strDir & "\venv\Scripts\python.exe"""
ElseIf objFSO.FileExists("C:\Users\p_pie\AppData\Local\Python\pythoncore-3.14-64\python.exe") Then
    strPython = """C:\Users\p_pie\AppData\Local\Python\pythoncore-3.14-64\python.exe"""
ElseIf objFSO.FileExists("C:\Windows\py.exe") Then
    strPython = "py.exe"
Else
    strPython = "python.exe"
End If

' Sprawdz czy pseudominizer_api.py istnieje
If Not objFSO.FileExists(strDir & "\pseudominizer_api.py") Then
    MsgBox "Nie znaleziono pseudominizer_api.py w:" & vbCrLf & strDir, _
           vbCritical, "Pseudominizer"
    WScript.Quit 1
End If

' Uruchom backend — widoczne okno CMD (/k: zostaje po awarii); log tylko w oknie, bez pliku (v1.4)
strCmd = "cmd /k cd /d """ & strDir & """ && " & strPython & _
         " -m uvicorn pseudominizer_api:app" & _
         " --host 127.0.0.1 --port 8765" & _
         " --log-level info"

objShell.Run strCmd, 1, False

' Poczekaj na start serwera
WScript.Sleep 3000

' Otworz przegladarke
objShell.Run "http://127.0.0.1:8765", 1, False

Set objShell = Nothing
Set objFSO   = Nothing
