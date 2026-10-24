# wb-armor 2.1（重构版，无历史包袱）

WorkBuddy / CodeBuddy 本地反代 + 破甲 + 多源路由，供 Codex 与 DeepSeek Harness 使用。
只保留重构后的 **内核 + CLI + 单文件 GUI**；旧面板、旧探针、旧入口已全部删除。

## 一分钟上手

```powershell
cd "C:\Users\Administrator\Desktop\wb 一键破甲反代"
python -m wbarmor start          # 8788 → 4097 → 8792 → 8790
python -m wbarmor deploy-codex   # ~/.codex/config.toml + 绝对路径 catalog
python -m wbarmor deploy-dsh     # ~/.dsh/profiles/web/cordis.patch.yml
python -m wbarmor status
```

图形界面：双击 `启动.cmd`，或 `Start-Process pythonw gui\app.py`。

## 结构

```
wbarmor\core.py     纯函数内核：会话/token、模型目录、Codex/DSH 部署、服务控制、破甲、载荷、日志、计划任务
wbarmor\cli.py      python -m wbarmor <cmd>
gui\app.py          Tk 控制台（18 个动作 + 模型列表 + 载荷选择 + 输出区）
scripts\            start-all / supervisor / launch-app / bootstrap / patch-armor / verify / logs / fix-codex / open-codex / start-wb8788 / setup-dsh / build-release
lib\                log.mjs（Node JSONL）、wlog.ps1（PowerShell JSONL）
src\                ig5-bridge.mjs（8790）、opencode-bridge.mjs（8792）
gw\workbuddy2api\   反代源码（8788）
vendor\             IG5 载荷（flash / full / lazy）
config\             catalog 样本、DSH patch 样本
dev\                doctor / repair / fix-window / start-proxy / push-via-api（排障用）
```

## CLI 全命令

| 命令 | 作用 |
|---|---|
| `status` | 四端口 + `/health` JSON |
| `start` / `stop` | 起全链路 / 停（计划任务 + 按端口杀 owner） |
| `token [--show] [--refresh]` | 会话摘要（token 掩码）、可刷新 |
| `inject --token T` | 写回 `auth.deviceToken`（0600） |
| `models [--set ID]` | 列出 / 设默认模型（写 `config.toml`） |
| `deploy-codex` / `deploy-dsh [--headless]` | 客户端部署 |
| `sync-catalog` | 从 8790 拉真实清单重写 catalog |
| `probe` | 主链路 + 免费档各打一次并计时 |
| `armor {status\|patch\|restore\|verify}` | 模板破甲状态 / 打补丁 / 回滚 / 校验 |
| `payload [--set PATH]` | 查看 / 切换载荷 |
| `logs [--tail N] [--comp NAME]` | 合并查看 JSONL 日志 |
| `tasks {status\|install\|remove}` | 计划任务维护 |
| `open codex\|dsh` | 启动客户端 |

## 模型选择

`gui/app.py` 右侧列表来自 8790 `/models`（失败回落 8792），双击即写 `config.toml` 的 `model`，
当前默认项高亮。CLI 等价：`python -m wbarmor models --set deepseek-v4.1-flash-sg`。

## 日志

统一 JSONL：`logs/launcher.log`（启动与 GUI 事件）、`logs/ig5-*.log`、`logs/oc-*.log`、`logs/<port>.err.log`。
查看：`python -m wbarmor logs --comp launcher --tail 20` 或 `scripts\logs.ps1 -Comp launcher`。

## 工程约定

- 路径全部脚本自定位（`__file__` / `$PSScriptRoot`），目录名带空格或中文均可；
- PowerShell 脚本必须存为 **UTF-8 with BOM**，否则 PS 5.1 按 ANSI 解析中文会语法错；
- `.payload` 读取时去 BOM；Python 输出统一按 utf-8 重编码，避免 GBK 控制台崩溃。

## 已知边界

- 端口全局独占，同机不能同时跑两套；
- `deploy-dsh` 覆盖现有 profile（自动 `.bak`）；
- 免费档（8792）无工具协议，仅文本；主链路 429 时自动兜底到免费档。
