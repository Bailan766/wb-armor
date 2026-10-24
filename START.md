# 启动方式

## 双击 `启动.cmd`（推荐，最稳）
不依赖任何打包，纯 PowerShell。会自动：起四进程 → 打开控制台窗口。
> 受限 TEMP / 无写权限环境也能用，不会解压任何东西。

## 双击 `wb-armor.exe`（可选）
单文件启动器，效果同上（PyInstaller 打包，需能写入 `%TEMP%` 自解压）。
若双击**无反应/报 Could not create temporary directory**，就是环境不允许自解压 —— 改用 `启动.cmd`。

## 命令行
```powershell
.\wbarmor.ps1 up          # 起四进程
.\wbarmor.ps1 status      # 端口 + /health
.\wbarmor.ps1 gui         # 起服务 + 开 GUI
.\wbarmor.ps1 setup       # 配 Codex(8790) + 客户端破甲
.\wbarmor.ps1 setup-dsh   # 配 DeepSeek Harness(8790) + 破甲 persona
.\wbarmor.ps1 setup -Dsh  # 一次配好两端
.\wbarmor.ps1 patch       # 模板破甲
.\wbarmor.ps1 payload full   # 切载荷 flash|full|lazy
```

## 首次准备
1. 装 Python 3.10+、Node 18+、opencode CLI。
2. `gw\workbuddy2api\` 是 submodule：`git submodule update --init --recursive`
3. 首次登录：GUI「🌐 浏览器登录」或 `wbarmor.ps1` 里的 setup 流程。
