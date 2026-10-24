# 启动方式（简洁版）

## 最简：双击 `wb-armor.exe`
- exe 与 `wbarmor.ps1`、`gui\`、`gw\`、`vendor\`、`ig5-bridge.mjs` 等**放在同一目录**（仓库根）。
- 双击后自动：起四进程（幂等）→ 打开控制台窗口。
- 窗口里一个大按钮 **▶ 一键启动**，其余按钮按需点。关掉窗口不影响后台服务。

> 说明：exe 是 PyInstaller 单文件包，双击后会先自解压到 `%TEMP%` 再运行（首次约 3–5 秒）。
> 若在**受限沙箱/无写权限的 TEMP** 环境双击无反应，直接用下面的 `启动.cmd`（不依赖解压）。

## 次简：双击 `启动.cmd`
- 纯 PowerShell，无需 Python 打包环境，最稳。
- 等价命令：`powershell -NoProfile -ExecutionPolicy Bypass -File wbarmor.ps1 gui`

## 命令行
```powershell
.\wbarmor.ps1 up        # 起四进程
.\wbarmor.ps1 status    # 看端口 + /health
.\wbarmor.ps1 gui       # 起服务 + 开 GUI
.\wbarmor.ps1 setup     # 配 Codex(8790) + 客户端破甲
.\wbarmor.ps1 patch     # 模板破甲
.\wbarmor.ps1 payload full   # 切载荷 flash|full|lazy
```

## 目录结构（整理后）
```
wb-armor/
├─ wb-armor.exe            双击启动（GUI）
├─ 启动.cmd / 启动.ps1      纯脚本启动（无 exe 时用）
├─ wbarmor.ps1             统一入口（up/down/status/gui/setup/patch/payload）
├─ start-all.ps1           四进程拉起（被 wbarmor 调用）
├─ ig5-bridge.mjs          8790 主桥（载荷注入/路由/兜底）
├─ opencode-bridge.mjs     8792 免费档 OpenAI 壳
├─ generate-client-armor.py 给 Codex catalog / DSH persona 上破甲
├─ gui/                    wbarmor_gui.py（控制台）+ launcher.py（exe 源码）+ selftest.py
├─ gw/workbuddy2api/       反代（上游 submodule: Zhengyuuuui/workbuddy2api）
├─ vendor/dsh-infinite-gen-5/  三档破甲载荷（MIT, SunsetRNE）
├─ tools/probes/           各种 probe 脚本（开发用，非必需）
├─ tools/legacy/           旧配置转储 / 早期破甲片段（历史）
├─ assets/                 截图等
└─ README.md / CREDITS.md / LICENSE / PUSH.md
```
