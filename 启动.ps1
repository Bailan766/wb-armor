# 一键启动 wb-armor 图形控制台（双击即可，无参数）
# 双击后由 wbarmor.ps1 gui 完成：起四进程 -> 自检 -> 拉起 GUI（pythonw，无控制台窗口）
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $here 'wbarmor.ps1') gui
