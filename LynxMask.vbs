' LynxMask.vbs — jedna ikona: uruchamia silnik (jeśli nie działa) i otwiera aplikację.
' LYNX-ONE-LAUNCHER (19.10.2026). Bez okna konsoli; log silnika nie trafia na dysk (S5).
' Stałe rozwiązanie (aplikacja sama zarządza silnikiem): LYNX-APP-LAUNCHER.
Option Explicit

Dim sh, fso, repo, backendDir, exe, i
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

repo       = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = repo & "\backend"
exe        = repo & "\frontend\src-tauri\target\release\pseudominizer.exe"

If Not fso.FileExists(exe) Then
    MsgBox "Aplikacja nie jest zbudowana." & vbCrLf & "Uruchom build.bat w folderze:" & vbCrLf & repo, _
           vbExclamation, "LynxMask"
    WScript.Quit 1
End If

If Not EngineReady() Then
    sh.CurrentDirectory = backendDir
    On Error Resume Next
    sh.Run "py -3 pseudominizer_api.py", 0, False      ' 0 = bez okna
    If Err.Number <> 0 Then
        MsgBox "Nie znaleziono Pythona (polecenie py)." & vbCrLf & "Zainstaluj Python 3 z python.org.", _
               vbCritical, "LynxMask"
        WScript.Quit 1
    End If
    On Error GoTo 0
    For i = 1 To 120                                    ' do 2 minut: wczytanie modelu i próby startowe
        WScript.Sleep 1000
        If EngineReady() Or fso.FileExists(backendDir & "\startup_error.json") Then Exit For
    Next
End If

sh.Run """" & exe & """", 1, False                     ' aplikacja sama pokaże ekran awarii, jeśli silnik nie wstał

' Silnik gotowy = odpowiada na /health i zapisał token dostępu (zapisuje go dopiero po próbach startowych).
Function EngineReady()
    Dim http
    EngineReady = False
    If Not fso.FileExists(backendDir & "\api_token.txt") Then Exit Function
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 1000, 1000, 1000, 1000
    http.open "GET", "http://127.0.0.1:8765/health", False
    http.send
    If Err.Number = 0 Then
        If http.status = 200 Then EngineReady = True
    End If
    On Error GoTo 0
End Function
