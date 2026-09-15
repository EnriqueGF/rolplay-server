# Reinicia el cliente contra localhost y hace login.
# Uso: .\relogin.ps1 [-User prueba] [-Pass clave] [-GameDir ..\..\game]
param([string]$User='prueba', [string]$Pass='clave', [string]$GameDir)
. (Join-Path $PSScriptRoot 'ui.ps1')
Get-Process RPcliente -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1
Start-Process -FilePath (Join-Path $GameDir 'RPcliente.exe') -ArgumentList '-local','-nocheck' -WorkingDirectory $GameDir
$login=[IntPtr]0
for($i=0; $i -lt 40 -and $login -eq [IntPtr]0; $i++){ Start-Sleep -m 500; $login=Find-Win 'Rolplay.net ver*' }
if($login -eq [IntPtr]0){ throw 'No aparece la ventana de login' }
$tb=@(); $btn=@()
foreach($k in [WA]::Kids($login)){ $c=[WA]::Cls($k); if($c -eq 'ThunderRT6TextBox'){ $tb+=$k }; if($c -eq 'ThunderRT6UserControlDC'){ $btn+=$k } }
$tb = $tb | Sort-Object { $r=New-Object WA+RECT; [WA]::GetWindowRect($_,[ref]$r)|Out-Null; $r.T }   # usuario arriba, pass abajo
TypeInto $tb[0] $User; TypeInto $tb[1] $Pass; Start-Sleep -m 300
$btn = $btn | Sort-Object { $r=New-Object WA+RECT; [WA]::GetWindowRect($_,[ref]$r)|Out-Null; $r.T }   # Acceder es el primero
RealClick $btn[0] $login
$main=[IntPtr]0
for($i=0; $i -lt 30 -and $main -eq [IntPtr]0; $i++){ Start-Sleep -m 500; $main=Get-MainWin }
if($main -eq [IntPtr]0){ "login sin ventana principal (¿servidor arrancado?)" } else { "login OK, ventana principal $main" }
