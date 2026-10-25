param([switch]$Quiet)
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinFix {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
'@

$SW_RESTORE = 9
$SWP_SHOWWINDOW = 0x40
$screenW = [WinFix]::GetSystemMetrics(0)
$screenH = [WinFix]::GetSystemMetrics(1)
$pids = @(Get-Process ChatGPT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
if ($pids.Count -eq 0) { if (-not $Quiet) { 'WIN no ChatGPT process' }; exit 1 }

$moved = 0
$seen = 0
$cb = [WinFix+EnumProc]{
  param($h, $l)
  $owner = 0
  [void][WinFix]::GetWindowThreadProcessId($h, [ref]$owner)
  if ($pids -notcontains [int]$owner) { return $true }
  $sb = New-Object System.Text.StringBuilder 512
  [void][WinFix]::GetWindowText($h, $sb, 512)
  if ($sb.Length -eq 0) { return $true }
  if (-not [WinFix]::IsWindowVisible($h)) { return $true }
  $script:seen++
  $r = New-Object WinFix+RECT
  [void][WinFix]::GetWindowRect($h, [ref]$r)
  $w = $r.R - $r.L; $hgt = $r.B - $r.T
  $off = ($r.L -lt 0) -or ($r.T -lt 0) -or ($r.L -ge $script:screenW) -or ($r.T -ge $script:screenH) -or ($w -le 50) -or ($hgt -le 50)
  if ($off) {
    $nw = [Math]::Min(1400, $script:screenW - 60)
    $nh = [Math]::Min(860, $script:screenH - 60)
    $nx = [Math]::Max(20, [int](($script:screenW - $nw) / 2))
    $ny = [Math]::Max(20, [int](($script:screenH - $nh) / 2))
    [void][WinFix]::ShowWindow($h, $SW_RESTORE)
    [void][WinFix]::SetWindowPos($h, [IntPtr]::Zero, $nx, $ny, $nw, $nh, $SWP_SHOWWINDOW)
    [void][WinFix]::SetForegroundWindow($h)
    $script:moved++
    if (-not $Quiet) { 'WIN moved "{0}" from {1},{2} to {3},{4} {5}x{6}' -f $sb.ToString(), $r.L, $r.T, $nx, $ny, $nw, $nh }
  }
  return $true
}
[void][WinFix]::EnumWindows($cb, [IntPtr]::Zero)
if (-not $Quiet) { 'WIN screen={0}x{1} windows={2} moved={3}' -f $screenW, $screenH, $seen, $moved }
