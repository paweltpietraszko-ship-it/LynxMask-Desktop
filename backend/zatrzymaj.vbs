' zatrzymaj.vbs v1.0 — Pseudominizer
' Zatrzymuje serwer, czyści __pycache__ i hardware_profile.json
' Uruchom przed zamknieciem lub podmiana plikow

Option Explicit

Dim objShell, objFSO, strDir

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

strDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 1. Zabij proces na porcie 8765
objShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -aon ^| findstr :8765') do taskkill /f /pid %a", 0, True

' 2. Wyczysc __pycache__
Dim strCache
strCache = strDir & "\__pycache__"
If objFSO.FolderExists(strCache) Then
    objFSO.DeleteFolder strCache, True
End If

' 3. Wyczysc hardware_profile.json
Dim strHW
strHW = strDir & "\hardware_profile.json"
If objFSO.FileExists(strHW) Then
    objFSO.DeleteFile strHW, True
End If

MsgBox "Pseudominizer zatrzymany." & vbCrLf & "__pycache__ i hardware_profile.json usuniete.", _
       vbInformation, "Pseudominizer"

Set objShell = Nothing
Set objFSO   = Nothing
