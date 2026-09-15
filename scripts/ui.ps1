# Helpers para manejar RPcliente.exe desde PowerShell sin robar el foco.
# Uso: . .\ui.ps1  (define $GameDir si el juego no está en ..\..\game)
if (-not $GameDir) { $GameDir = Join-Path $PSScriptRoot '..\..\game' }
$ShotDir = Join-Path $PSScriptRoot '..\shots'
if (-not (Test-Path $ShotDir)) { New-Item -ItemType Directory $ShotDir | Out-Null }
Add-Type -AssemblyName System.Drawing
if (-not ('WA' -as [type])) {
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class WA {
 public delegate bool EnumProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc f, IntPtr l);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
 [DllImport("user32.dll")] public static extern IntPtr PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,int dx,int dy,uint d,UIntPtr e);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,IntPtr a,int x,int y,int cx,int cy,uint fl);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X,Y; }
 public static List<IntPtr> Tops(uint pid){ var l=new List<IntPtr>(); EnumWindows((h,x)=>{ uint p; GetWindowThreadProcessId(h,out p); if(p==pid && IsWindowVisible(h)) l.Add(h); return true;}, IntPtr.Zero); return l; }
 public static List<IntPtr> Kids(IntPtr p){ var l=new List<IntPtr>(); EnumChildWindows(p,(h,x)=>{ l.Add(h); return true;}, IntPtr.Zero); return l; }
 public static string Cls(IntPtr h){ var s=new StringBuilder(128); GetClassName(h,s,128); return s.ToString(); }
 public static string Txt(IntPtr h){ var s=new StringBuilder(2048); GetWindowText(h,s,2048); return s.ToString(); } }
"@
}
[WA]::SetProcessDPIAware() | Out-Null

function Get-RPPid { (Get-Process RPcliente -ErrorAction SilentlyContinue | Select-Object -First 1).Id }
function Find-Win($pattern){ foreach($h in [WA]::Tops((Get-RPPid))){ if([WA]::Txt($h) -like $pattern){ return $h } }; return [IntPtr]0 }
# La ventana principal es el formulario que contiene la casilla 'Aceptar Privados'.
function Get-MainWin { foreach($h in [WA]::Tops((Get-RPPid))){ if([WA]::Cls($h) -ne 'ThunderRT6FormDC'){ continue }; foreach($k in [WA]::Kids($h)){ if([WA]::Cls($k) -eq 'ThunderRT6CheckBox' -and [WA]::Txt($k) -eq 'Aceptar Privados'){ return $h } } }; return [IntPtr]0 }
function Get-SubWin { $m=Get-MainWin; foreach($h in [WA]::Tops((Get-RPPid))){ if([WA]::Cls($h) -eq 'ThunderRT6FormDC' -and $h -ne $m){ return $h } }; return [IntPtr]0 }

# Captura solo una ventana del cliente (PrintWindow), nunca el escritorio completo.
function Shot($h, $name){ $r=New-Object WA+RECT; [WA]::GetWindowRect($h,[ref]$r)|Out-Null; $w=$r.R-$r.L; $hh=$r.B-$r.T; if($w -lt 5 -or $hh -lt 5){ return }; $bmp=New-Object System.Drawing.Bitmap $w,$hh; $g=[System.Drawing.Graphics]::FromImage($bmp); $hdc=$g.GetHdc(); [WA]::PrintWindow($h,$hdc,2)|Out-Null; $g.ReleaseHdc($hdc); $bmp.Save((Join-Path $ShotDir $name)); $g.Dispose(); $bmp.Dispose() }

# Texto en TextBox: WM_CHAR carácter a carácter (dispara el evento Change de VB).
function TypeInto($h,$s){ [WA]::SendMessage($h,0x000C,[IntPtr]0,[string]"")|Out-Null; foreach($ch in $s.ToCharArray()){ [WA]::SendMessage($h,0x0102,[IntPtr][int]$ch,[IntPtr]1)|Out-Null } }

# Los botones JwldButn solo responden con fiabilidad a un clic real: ventana topmost, cursor al botón, clic, restaurar.
function RealClick($ctl, $topwin){
  $p=New-Object WA+POINT; [WA]::GetCursorPos([ref]$p)|Out-Null
  [WA]::SetWindowPos($topwin,[IntPtr](-1),0,0,0,0,0x0013)|Out-Null; Start-Sleep -m 150
  $r=New-Object WA+RECT; [WA]::GetWindowRect($ctl,[ref]$r)|Out-Null
  [WA]::SetCursorPos([int](($r.L+$r.R)/2),[int](($r.T+$r.B)/2))|Out-Null; Start-Sleep -m 120
  [WA]::mouse_event(0x0002,0,0,0,[UIntPtr]::Zero); Start-Sleep -m 80; [WA]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero); Start-Sleep -m 200
  [WA]::SetWindowPos($topwin,[IntPtr](-2),0,0,0,0,0x0013)|Out-Null
  [WA]::SetCursorPos($p.X,$p.Y)|Out-Null
}

function Get-Btns($win){ $r0=New-Object WA+RECT; [WA]::GetWindowRect($win,[ref]$r0)|Out-Null; $l=@(); foreach($k in [WA]::Kids($win)){ if([WA]::Cls($k) -eq 'ThunderRT6UserControlDC'){ $r=New-Object WA+RECT; [WA]::GetWindowRect($k,[ref]$r)|Out-Null; $l+=[pscustomobject]@{h=$k; x=$r.L-$r0.L; y=$r.T-$r0.T} } }; $l | Sort-Object y,x }
# Botones del lobby por orden vertical.
$MainButtons=@{'Enviar'=0;'Retos'=1;'Cartas'=2;'Intercambios'=3;'Salas'=4;'Estadisticas'=5;'Clanes'=6;'Manual'=8;'Salir'=9}
function Main-Btn($name){ $b=@(Get-Btns (Get-MainWin)); return $b[$MainButtons[$name]].h }

function Dump-Windows { $pid2=Get-RPPid; foreach($h in [WA]::Tops($pid2)){ $r=New-Object WA+RECT; [WA]::GetWindowRect($h,[ref]$r)|Out-Null; "win $h '$([WA]::Txt($h))' cls=$([WA]::Cls($h)) size=$($r.R-$r.L)x$($r.B-$r.T)" } }
function Dump-Kids($h){ foreach($k in [WA]::Kids($h)){ $r=New-Object WA+RECT; [WA]::GetWindowRect($k,[ref]$r)|Out-Null; "  kid $k cls=$([WA]::Cls($k)) text='$([WA]::Txt($k))' at $($r.L),$($r.T) $($r.R-$r.L)x$($r.B-$r.T)" } }
function New-Wins($before){ return @([WA]::Tops((Get-RPPid)) | Where-Object { $before -notcontains $_ }) }
function Close-Dialogs { foreach($h in [WA]::Tops((Get-RPPid))){ if([WA]::Cls($h) -eq '#32770'){ Shot $h 'lastdlg.png'; foreach($k in [WA]::Kids($h)){ if([WA]::Cls($k) -eq 'Button'){ [WA]::PostMessage($k,0x00F5,[IntPtr]0,[IntPtr]0)|Out-Null } } } }; Start-Sleep -m 800 }
function Close-Subforms { $m=Get-MainWin; foreach($h in [WA]::Tops((Get-RPPid))){ if([WA]::Cls($h) -eq 'ThunderRT6FormDC' -and $h -ne $m){ [WA]::PostMessage($h,0x0010,[IntPtr]0,[IntPtr]0)|Out-Null } }; Start-Sleep -m 800 }
# Abre una ventana del lobby (p. ej. 'Cartas') con reintentos y captura las ventanas nuevas.
function Open-Sub($name,$tag){ Close-Dialogs; Close-Subforms; $main=Get-MainWin; $new=@(); for($t=0;$t -lt 3 -and $new.Count -eq 0;$t++){ $before=[WA]::Tops((Get-RPPid)); RealClick (Main-Btn $name) $main; Start-Sleep 5; $new=New-Wins $before }; $i=0; foreach($h in $new){ "new $h '$([WA]::Txt($h))' $([WA]::Cls($h))"; Shot $h "$tag$i.png"; $i++ }; return $new }
# Estado de la ventana Cartas: combos, TreeViews y ListBoxes.
function Read-Cartas { $w=Get-SubWin; if($w -eq [IntPtr]0){ "no hay subventana"; return }; foreach($k in [WA]::Kids($w)){ $c=[WA]::Cls($k); $r=New-Object WA+RECT; [WA]::GetWindowRect($k,[ref]$r)|Out-Null; if($c -eq 'ThunderRT6ComboBox'){ "combo $k x=$($r.L) items=$([WA]::SendMessage($k,0x0146,[IntPtr]0,[IntPtr]0))" }; if($c -eq 'TreeView20WndClass'){ "treeview $k x=$($r.L) items=$([WA]::SendMessage($k,0x1105,[IntPtr]0,[IntPtr]0))" }; if($c -eq 'ThunderRT6ListBox'){ "listbox $k x=$($r.L) items=$([WA]::SendMessage($k,0x018B,[IntPtr]0,[IntPtr]0))" } } }
function Tail-Log($n=15){ Get-Content (Join-Path $PSScriptRoot '..\server\server.log') | Where-Object { $_ -match '<-|\?\?|->|Trace|Error' } | Select-Object -Last $n }
