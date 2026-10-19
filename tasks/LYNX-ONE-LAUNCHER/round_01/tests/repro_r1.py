"""Execute delivered VBS control flow under WSH with inert COM substitutes."""
import json
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[4]
source = (root/'LynxMask.vbs').read_text(encoding='utf-8')
# Keep branches/commands/quoting intact; replace only external effects.
source = source.replace('Option Explicit', '').replace('CreateObject(', 'AuditObject(')
source = source.replace('WScript.Sleep ', 'AuditSleep ').replace('MsgBox ', 'AuditMessage ')
header = r'''
Option Explicit
Dim auditMode, auditTicks
auditMode = WScript.Arguments(0)
auditTicks = 0
Function AuditObject(name)
 Select Case name
 Case "WScript.Shell": Set AuditObject = New AuditShell
 Case "Scripting.FileSystemObject": Set AuditObject = New AuditFSO
 Case "MSXML2.ServerXMLHTTP.6.0": Set AuditObject = New AuditHTTP
 Case Else: Err.Raise 1000
 End Select
End Function
Sub AuditSleep(n)
 auditTicks = auditTicks + 1
 WScript.Echo "WAIT " & auditTicks
End Sub
Sub AuditMessage(msg, style, title)
 WScript.Echo "MESSAGE " & title
End Sub
Class AuditFSO
 Public Function GetParentFolderName(path)
  GetParentFolderName = "C:\Audit repo"
 End Function
 Public Function FileExists(path)
  FileExists = False
  If InStr(path, "pseudominizer.exe") > 0 Then FileExists = (auditMode <> "missing_exe")
  If InStr(path, "api_token.txt") > 0 Then FileExists = (auditMode = "ready" Or (auditMode = "cold" And auditTicks >= 2))
  If InStr(path, "startup_error.json") > 0 Then FileExists = (auditMode = "startup_fail" And auditTicks >= 1)
 End Function
End Class
Class AuditShell
 Public CurrentDirectory
 Public Function Run(command, style, wait)
  WScript.Echo "RUN " & style & " " & command
  If Left(command, 2) = "py" And auditMode = "missing_py" Then Err.Raise 53
  Run = 0
 End Function
End Class
Class AuditHTTP
 Public status
 Public Sub setTimeouts(a,b,c,d)
 End Sub
 Public Sub open(a,b,c)
  If b <> "http://127.0.0.1:8765/health" Then Err.Raise 1001
 End Sub
 Public Sub send()
  status = 200
 End Sub
End Class
'''
summary = {}
with tempfile.TemporaryDirectory(prefix='lynx_launcher_wsh_') as d:
    script = pathlib.Path(d)/'harness.vbs'
    script.write_text(header+'\n'+source, encoding='utf-16')
    for mode in ['ready','cold','startup_fail','timeout','missing_exe','missing_py']:
        p = subprocess.run(['cscript.exe','//nologo',str(script),mode],capture_output=True,timeout=20)
        lines = p.stdout.decode('utf-8',errors='replace').splitlines()
        assert not p.stderr, (mode,p.stderr)
        starts = [x for x in lines if x.startswith('RUN 0 py -3 pseudominizer_api.py')]
        apps = [x for x in lines if x.startswith('RUN 1 "C:\\Audit repo\\frontend')]
        waits = sum(x.startswith('WAIT ') for x in lines)
        if mode in ['missing_exe','missing_py']:
            assert p.returncode == 1 and not apps and any(x.startswith('MESSAGE') for x in lines),(mode,lines)
        else:
            assert p.returncode == 0 and len(apps)==1,(mode,lines)
        assert len(starts) == int(mode not in ['ready','missing_exe']),(mode,lines)
        assert waits == {'ready':0,'cold':2,'startup_fail':1,'timeout':120,'missing_exe':0,'missing_py':0}[mode]
        summary[mode] = dict(engine_starts=len(starts),app_starts=len(apps),waits=waits,exit=p.returncode)
print(json.dumps(summary))
