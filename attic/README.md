# dev/patches —— 一次性修补脚本归档

这些文件是我在本机迭代过程中**临时写在桌面**的补丁脚本，现在收进项目，作为“某次改动是怎么做的”的可追溯记录。它们不是运行期依赖：`wbarmor` / `gui` / `scripts` 都不 import 它们。

## 清单

| 文件 | 改了什么 | 落到哪里 |
|---|---|---|
| `_patch_quote.py` | `Start-Process -ArgumentList` 里带空格路径加引号（`Q()` 函数） | `scripts/start-all.ps1`、`scripts/supervisor.ps1` |
| `_patch_login.py` | 登录入口改成 `/login?platform=&state=`，CDP 复用标签页 | `wbarmor/core.py`（`login_url` / `open_login_browser` / `_cdp_new_tab`） |
| `_patch_capture.py` | 抓取器过滤 `__BEACON_*` 埋点键，补登录页判定与失败话术 | `scripts/cdp-token.mjs`、`wbarmor/core.py` |
| `_patch_armor_capture2.py` | 统一破甲判据（有 canary 即 ARMOR-OFF）；CDP 选页跳过 `about:blank` | `wbarmor/core.py`、`scripts/cdp-token.mjs` |
| `_patch_payload.py` | 载荷解析改为「selector → 内置 vendor」，加 `reset_payload` | `wbarmor/core.py` |
| `_patch_gui_token.py` | 面板加「浏览器登录 / 抓取并注入」两个按钮 | `gui/app.py` |
| `_patch_armor_const.py` | 把破甲段固化为 `ARMOR_OFF_TEXT`，并注入 catalog / DSH | `wbarmor/core.py` |
| `_patch_dsh_schema.py` | DSH patch 从 mapping 改为**顶层数组 + id/config** | `wbarmor/core.py`（`_dsh_yaml`） |
| `_patch_dsh_key.py` | `deploy_dsh` 自动补 `DEEPSEEK_API_KEY`（用户级） | `wbarmor/core.py`（`_ensure_dsh_key`） |
| `_patch_dsh_insert.py` | `insert: dsh-infinite-gen-5` 只在已安装该插件的 profile 里写 | `wbarmor/core.py` |
| `_sync_check.py` / `_sync_inspect.py` / `_sync_apply.py` | 与上游 `Zhengyuuuui/workbuddy2api` 比对/同步的三个阶段脚本 | 已被 `scripts/gw-sync.py` 取代 |

## 注意

- 这些脚本里仍写着本机绝对路径（`C:\Users\Administrator\Desktop\wb 一键破甲反代`），属于历史记录，**不建议直接重跑**；对应能力已固化进 `wbarmor/core.py` 或 `scripts/*`。
- 想改现有行为，改 `wbarmor/core.py` / `scripts/*`，不要改这里。
- 上游同步现在用：

```powershell
python scripts\gw-sync.py            # 只比较
python scripts\gw-sync.py --apply    # 写入（自动备份到 _archive\）
```
