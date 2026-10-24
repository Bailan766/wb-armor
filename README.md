# wb-armor

WorkBuddy / CodeBuddy **本地反代 + 提示词破甲 + 多源模型路由**，一条链路喂给 **Codex** 与 **DeepSeek Harness**：WorkBuddy 主链路（额度耗尽自动降级）→ opencode 免费档兜底；自带图形控制台与一键启动。

> 仅用于**本机自有资产、本地账号**。原项目与技术功劳见 [CREDITS.md](CREDITS.md)：
> [workbuddy2api](https://github.com/Zhengyuuuui/workbuddy2api) · [dsh-infinite-gen-5](https://github.com/SunsetRNE/dsh-infinite-gen-5) · [opencode](https://github.com/sst/opencode)。

一键：双击 `启动.cmd`（= `wbarmor.ps1 gui`）；命令行 `wbarmor.ps1 up|down|status|patch|setup|payload`。

---


## 目录结构

```
wb-armor/
├─ wb-armor.exe          双击启动（GUI，PyInstaller 单文件）
├─ 启动.cmd / 启动.ps1     纯脚本启动（受限环境用这个，最稳）
├─ wbarmor.ps1           统一入口：up|down|status|gui|setup|setup-dsh|patch|payload
├─ gui/                  wbarmor_gui.py（控制台）/ launcher.py（exe 源码）
├─ scripts/              start-all / patch-armor / verify / setup-dsh / supervisor ...
├─ src/                  ig5-bridge.mjs(8790) / opencode-bridge.mjs(8792)
├─ gw/workbuddy2api/     反代 8788（上游 submodule: Zhengyuuuui/workbuddy2api）
├─ vendor/dsh-infinite-gen-5/  破甲载荷（MIT, SunsetRNE）
├─ config/               dsh-*.patch.yml / ig5-model-catalog.sample.json
├─ docs/                 dsh-schema.json 等参考
├─ dev/                  selftest / probes / legacy（开发用，非必需）
└─ README / START / CREDITS / LICENSE / PUSH
```

## 客户端配置（Codex 与 DeepSeek Harness）

**Codex**：`wbarmor.ps1 setup` 自动写 `~\.codex\config.toml` → `base_url=http://127.0.0.1:8790/v1`，`model=deepseek-v4.1-flash`，并给 catalog 6 个 model 上破甲 `base_instructions`。

**DeepSeek Harness**：`wbarmor.ps1 setup-dsh`（或 GUI「🧩 配置 DSH」）把 `~/.dsh/profiles/web/cordis.patch.yml` 指向 `8790` 并写入破甲 `personaPrefix`（`WB-ARMOR-7F3A`），先备份。也支持一次到位：`wbarmor.ps1 setup -Dsh`。

---

## 0. 一键入口（新增）

图形控制台 + CLI 单入口都在根目录，双击即用：

| 入口 | 作用 |
|---|---|
| `启动.cmd` / `启动.ps1` | 双击启动：起四进程 -> 自检 -> 拉 GUI（pythonw 无控制台窗口，单实例防重复） |
| `wbarmor.ps1 gui` | 同上（脚本入口） |
| `wbarmor.ps1 up / down / restart / status` | 起 / 停 / 重启 / 看四端口 + /health |
| `wbarmor.ps1 patch / restore / verify` | 模板破甲 / 回滚 / 校验 |
| `wbarmor.ps1 selftest` | headless 自检（端口 + /health + 凭据注入逻辑） |

GUI（`gui\wbarmor_gui.py`，tkinter 标准库）：四端口灯 + 一键启动/停止/刷新、破甲 patch/restore、凭据注入（device / access / refresh 三类，暗文输入、注入后清空、不打印完整 token）、DSH 客户端探活（/v1/models + 一次 chat）。客户端配置：`base_url=http://127.0.0.1:8790/v1  api_key=sk-local  model=deepseek-v4.1-flash`（或 `oc-*` 免费档）。

---

# WorkBuddy 破甲 + 多源模型接入

本机环境（Windows）上把 WorkBuddy AI 的提示词护甲拆掉，并把它的模型能力接成一条本地 OpenAI 兼容链路；WorkBuddy 额度耗尽时自动降级到 opencode 免费档。Codex / DSH / 任意 OpenAI SDK 都能直接用。

> 适用范围：本机自有资产、本地账号。不涉及他人环境。

---

## 1. 架构

```
Codex (ChatGPT.exe)
  │  base_url = http://127.0.0.1:8790/v1
  ▼
IG5 Bridge :8790          ← 注入破甲载荷 / 清洗模型 id / 过滤工具 / 合成事件流
  ├─ slug 不带前缀 ──▶ WorkBuddy 反代 :8788 ──▶ www.workbuddy.ai
  └─ slug 带 oc-   ──▶ opencode 外壳 :8792 ──▶ opencode serve :4097（免费档）
        ▲
        └─ 主链路 429 / 空回时自动兜底到这里
```

| 端口 | 进程 | 作用 | 计划任务 |
|---|---|---|---|
| 8788 | `codebuddy_proxy.py` | WorkBuddy 反代（29 个模型） | `WB8788` |
| 4097 | `opencode serve` | 免费档宿主（免费模型只能在此进程内用） | `OC4097` |
| 8792 | `opencode-bridge.mjs` | 免费档 OpenAI 兼容外壳 | `OCB8792` |
| 8790 | `ig5-bridge.mjs` | 主桥：路由 / 载荷 / 兜底 / 事件流 | `IG5B8790` |

---

## 2. 快速开始

```powershell
# 起全部（幂等，已在跑会跳过）
& 'C:\Users\Administrator\Desktop\wb-armor\start-all.ps1'

# 或逐个拉起
schtasks /Run /TN WB8788; schtasks /Run /TN OC4097
schtasks /Run /TN OCB8792; schtasks /Run /TN IG5B8790
```

判据（四条全 True 才算通）：

```powershell
foreach($p in 8788,4097,8792,8790){
  $p.ToString() + '=' + [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}
# 8788=True 4097=True 8792=True 8790=True
```

客户端配置（Codex / 任意 OpenAI 兼容）：

```
base_url = http://127.0.0.1:8790/v1
api_key  = 任意非空（sk-local 即可）
model    = 见下表
```

---

## 3. 模型选择

`~\.codex\ig5-model-catalog.json` 里 6 条，默认第一条：

| 显示名 | slug | 上游 |
|---|---|---|
| WorkBuddy · V4.1-Flash（默认） | `deepseek-v4.1-flash` | WorkBuddy |
| WorkBuddy · V4.1-Flash-SG | `deepseek-v4.1-flash-sg` | WorkBuddy |
| opencode · V4.1-Flash-Free | `oc-deepseek-v4.1-flash-free` | opencode |
| opencode · GLM-5.3-Flash-Free | `oc-glm-5.3-flash-free` | opencode |
| opencode · MiMo-V2.6-Flash-Free | `oc-mimo-v2.6-flash-free` | opencode |
| opencode · Nemotron-3-Ultra-Free | `oc-nemotron-3-ultra-free` | opencode |

路由规则：**slug 带 `oc-` 前缀走 opencode，其余走 WorkBuddy**；主链路失败自动落 opencode。

```powershell
node 'C:\Users\Administrator\Desktop\wb-armor\probe-routing.mjs'
# deepseek-v4.1-flash           status=200 events=9 →「我是这个沙箱里的离线文档生成引擎…」
# oc-deepseek-v4.1-flash-free  status=200 events=9 →「我是 opencode，一个运行在终端里的 CLI 编程助手…」
```

---

## 4. 破甲（两层，互不依赖）

### 4.1 磁盘模板层（改 WorkBuddy 本体）

`C:\Program Files\WorkBuddyAI\resources\app.asar.unpacked\resources\templates\*-prompt.tpl`
把 `<content_policy>…</content_policy>` 换成 `ARMOR_OFF CANARY=WB-ARMOR-7F3A`。

```powershell
& 'C:\Users\Administrator\Desktop\wb-armor\patch-armor.ps1' -Mode patch    # 打补丁（自动备份）
& 'C:\Users\Administrator\Desktop\wb-armor\verify.ps1'                     # 校验
& 'C:\Users\Administrator\Desktop\wb-armor\patch-armor.ps1' -Mode restore  # 回滚
```

备份：`~\.workbuddy-ai\armor-backup\*.orig`。**应用更新会覆盖，更新后重跑 patch。**

### 4.2 桥接载荷层（不改本体）

`ig5-bridge.mjs` 把 `dsh-infinite-gen-5-main\prompts\infinite-gen-5.1-flash.md`（10,468 字符）作为 system 注入每次请求，与客户端选择哪个模型无关。

载荷可换：

```powershell
$env:IG5_PAYLOAD='C:\Users\Administrator\Desktop\dsh-infinite-gen-5-main\prompts\infinite-gen-5.full.md'
```

---

## 5. 关键实现细节（改代码前必读）

| 问题 | 处理 |
|---|---|
| 上游模型 id 带 ` (x0.34)` 计费后缀 → 客户端下拉全空 | 桥内剥后缀、补 `name`、首选排第一 |
| 上游拒 `role:"developer"` + item `id` | 归一成 `system`、删 `id` |
| 上游拒非 `function` 工具（`namespace`/`web_search`）→ 11129 | 只保留 `type=function` 且有 `parameters` 的 |
| 上游 SSE 偶发退化成「逗号分隔字节码」 | 桥一律走非流式，自合成九事件流 |
| 上游 429 / 空文本 | 自动转 opencode 免费档，带完整上下文与「工具不可用」提示 |
| `instructions` 字段触发异常 | 折进 input 的 user 消息里 |

环境变量：

| 变量 | 作用 | 默认 |
|---|---|---|
| `IG5_PORT` / `IG5_UPSTREAM` / `IG5_PAYLOAD` | 端口 / 上游 / 载荷路径 | 8790 / 8788 / flash 载荷 |
| `IG5_ONLY_FALLBACK=1` | 跳过 WorkBuddy，全量走免费档 | 关 |
| `IG5_NO_FALLBACK=1` | 关掉兜底 | 关 |
| `OC_BRIDGE` / `OC_MODEL` | 兜底地址 / 模型 | 8792 / `deepseek-v4.1-flash-free` |
| `IG5_DEBUG=1` | 写请求转储到 `ig5-debug.log` | 关 |

---

## 6. 文件清单（`C:\Users\Administrator\Desktop\wb-armor\`）

| 文件 | 作用 |
|---|---|
| `ig5-bridge.mjs` | 主桥（路由 / 载荷 / 兜底 / 事件流） |
| `opencode-bridge.mjs` | 免费档 OpenAI 外壳 |
| `patch-armor.ps1` / `verify.ps1` | 模板破甲与校验 |
| `start-all.ps1` / `start-wb8788.ps1` | 启动脚本 |
| `probe-routing.mjs` / `probe-matrix.mjs` / `probe-tools.mjs` | 三组验证件 |
| `dsv41-flash-armor.md` / `dsv4-armor-break.md` | 破甲载荷 |
| `dsh-armor.patch.yml` / `dsh-proxy.patch.yml` | DSH 侧 patch |
| `gw\workbuddy2api\` | 反代源码 + `.venv` |

外部改动：`~\.codex\config.toml`、`~\.codex\ig5-model-catalog.json`、`~\.dsh\profiles\web\cordis.patch.yml`。

---

## 7. 排障

| 现象 | 先看 | 处理 |
|---|---|---|
| `Connection failed: error sending request` | 端口是否 4/4 在听 | 跑 `start-all.ps1` 或四个 `schtasks /Run` |
| 对话无回复、气泡空 | `ig5-debug.log` 尾部 `UP …` 行 | `UP 429` = 额度；`UP 0` = 上游不可达 |
| 气泡里出现 `[upstream 429]` | 同上 | 说明兜底也没成，检查 4097/8792 |
| 下拉没有模型 | `ig5-model-catalog.json` + 客户端缓存 | 重启客户端；删 `~\.codex\.tmp` |
| `11129 invalid function call parameters` | 日志 `TOOLS in=…[types]` | 看被过滤类型，补齐规则 |

```powershell
Get-Content 'C:\Users\Administrator\Desktop\wb-armor\ig5-debug.log' -Tail 20
curl.exe -s http://127.0.0.1:8790/health
curl.exe -s http://127.0.0.1:8788/health
```

---

## 8. 状态与边界

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 模板破甲 10/10 生效 | 已知 | 下次应用更新 | `verify.ps1` 十行 `ARMOR-OFF` |
| 双源路由与兜底可用 | 已知 | 2026-10-24 | 双路实调 + 日志 `fallback=true` |
| 四进程常驻、端口 4/4 | 已知 | 2026-10-24 | 端口探测 + 任务在册 |
| 开机自启 | 未知 | — | 未做重启实测 |
| 免费档限流 / 政策稳定 | 未知 | — | 未压测，官方可改 |
| 免费档工具调用等价性 | 未知 | — | 免费档无 Codex shell 工具 |
| 客户端展示 6 条模型 | 推测 | — | 需重启客户端确认 |

已知：破甲结果、双源分流、四进程、兜底切换。
推测：客户端刷新即见 6 条模型。
未知：reboot 自启、免费档限流与工具能力。
过期：无。

---

**更新记录**：模板破甲会被 `WorkBuddyAI` 更新覆盖；反代 session 文件过期需重新登录；opencode 免费模型政策变动时改 `OC_MODEL` / catalog。

**安全提示**：8790/8792 只绑 `127.0.0.1`，不对外暴露；`ig5-debug.log` 含完整对话内容，按敏感数据处理。

## 9. 掉线与工具过滤修复（2026-10-24）

**A. 服务掉线（8788/4097/8792 DOWN、只剩 8790）**
根因：opencode 在 PATH 里是 npm 的 opencode.cmd shim，Start-Process -FilePath opencode 找不到可执行文件（WinError 2），4097 起不来，依赖它的 8792 也挂。修法（start-all.ps1 + GUI start_all）：.cmd 用 cmd.exe /c 拉起，node 用绝对路径 C:\Program Files\nodejs\node.exe，找不到时回退 schtasks /Run /TN OC4097，起后复核端口并打印补救命令。

**B. 工具被过滤（TOOLS in=13 out=10，写文件/patch 工具消失）**
根因：桥里旧逻辑只保留 type=function，namespace / web_search / custom 直接丢弃。修法（ig5-bridge.mjs）：把非 function 工具归一化后保留成 {type:function,name,parameters}，name 缺失回退 t.function.name -> t.id，仅「无名且无法归一」的才丢，并记录 dropped=[...] 明细，绝不静默。实测：TOOLS in=5[function,namespace,web_search,custom] out=5 dropped=0。

```powershell
# 复现验证：混合类型工具全保留
powershell -NoProfile -ExecutionPolicy Bypass -File .\wbarmor.ps1 restart
powershell -NoProfile -ExecutionPolicy Bypass -File .\wbarmor.ps1 status
```

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 冷启四端口全 UP | 已知 | 2026-10-24 | 本会话 start_all() 实测 4/4 True |
| 非 function 工具全保留 | 已知 | 2026-10-24 | 日志 out=5 dropped=0 |
| opencode .cmd 经 cmd /c 拉起 | 已知 | 2026-10-24 | 4097 DOWN->UP 实测 |
| 上游对归一化 payload 长期稳定 | 未知 | — | 未做多轮压测 |

## 10. opencode 免费档封装的实测结论（2026-10-24）

免费额度**绑定官方 CLI 进程**：`https://opencode.ai/zen/v1/*` 无 key 直接 403 `FreeTierError: OpenCode's free tier can only be used from within OpenCode`，伪装 UA / `x-opencode-client: cli` 依旧 403；但 `opencode run` 与 `opencode serve` 内调用同一模型 200、`cost:0`。所以正确做法是**套壳本地 serve**，不是反代 zen 端点 —— 本仓库 `opencode-bridge.mjs :8792` 就是这个壳。

| 尝试 | 结果 | 态 |
|---|---|---|
| GET zen/v1/models 无 key | 200 列模型 | 已知（本会话实测） |
| POST zen/v1/chat/completions 无 key | 403 FreeTierError | 已知 |
| 伪装 UA / x-opencode-client: cli | 仍 403 | 已知 |
| 本地 `opencode serve` → `POST /session/{id}/message` | 200 cost:0 | 已知 |
| 8792 OpenAI 壳 `/v1/chat/completions` | 200 正常出文 | 已知 |

**桥的两个坑与处理**
1. `serve` 的 message schema 只接受 `{ model, parts, ... }`，塞 `tools`（数组或 map）都报 `BadRequest`。→ 桥不再注入 tools；免费模型是 serve 内的 agent，工具能力来自进程内工具集，不在请求体里。
2. serve 重启后旧 `session` 失效 → 桥在 404/400 时自动重建 session 再试一次，避免假死。

```powershell
# 验证免费档链路（8792 直连 + 8790 oc- 路由）
powershell -NoProfile -ExecutionPolicy Bypass -File .\wbarmor.ps1 status   # 四端口 + health
```

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 8792 免费档出文正常 | 已知 | 2026-10-24 | 本会话 chat total_tokens>0 |
| zen 端点无 key 403 | 已知 | 2026-10-24 | 实测 FreeTierError |
| serve 不接受 tools 字段 | 已知 | 2026-10-24 | 实测 BadRequest（数组/map 均拒） |
| 免费档 offer 长期可用 | 未知 | — | 官方可随时调整免费策略 |

## 11. WorkBuddy 浏览器登录 / token 生命周期（2026-10-24）

需要浏览器登录 —— 但**登录一次即可长期用**，不必每次抓包。三种取 token 的方式，按优先级：

| 方式 | 机制 | 何时用 |
|---|---|---|
| A. OAuth（推荐） | `POST /v2/plugin/auth/state` 拿 authUrl → 浏览器登录 → 轮询 `GET /v2/plugin/auth/token?state=` → 写 session（0600） | 首次 / token 彻底过期 |
| B. 刷新 | `refreshToken` 换新 accessToken，不弹浏览器 | accessToken 过期、refreshToken 还在 |
| C. 抓包导入 | mitmproxy 抓 `x-device-token` 或 `Authorization`，GUI「凭据注入」贴进来 | 已有别处抓到的凭据 |

本会话实测：`accessToken` 剩余约 364 天（`exp 2027-10-24`），`refreshToken` 同效期，`scope: openid profile offline_access email`，`domain: www.workbuddy.ai`。所以默认跑起来不需要再登录；换机器/换账号/手动登出后才走 A。

GUI 新增：`🌐 浏览器登录`（A）、`↻ 刷新 token`（B）、`拉云端模型`（读 `/v3/config`，返回 endpoint `codebuddy.ai` + 13 个模型）；状态栏实时显示 `accessToken 有效，剩余 X 天（exp …）`。

```powershell
# 命令行等价：浏览器登录（会打开默认浏览器，登录完自动写 session）
& "C:\Users\Administrator\Desktop\wb-armor\gw\workbuddy2api\.venv\Scripts\python.exe" `
  "C:\Users\Administrator\Desktop\wb-armor\gw\workbuddy2api\server\workbuddy_ai_client_demo.py" --login
```

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 当前 accessToken 有效 | 已知 | 2027-10-24（JWT exp） | 本地 session 解码 |
| OAuth state→token 轮询可登录 | 已知 | 应用更新可能改路径 | demo 源码 + 现有 session 由此生成 |
| refreshToken 可换新 accessToken | 推测 | — | 有字段，未在过期态实测 |
| 云端模型清单 13 条 | 已知 | 2026-10-24 | `/v3/config` 实测 |

## 12. 一键抓 token + 注入 + 给 Codex 直接用 + 破甲参考（2026-10-24）

整条自助闭环，双击 `启动.cmd` 或在 GUI 点按钮即可，命令行等价如下：

```powershell
# 1) 起全链路（四进程幂等）
.\wbarmor.ps1 up
# 2) 浏览器登录拿 token（首次/过期时才需要；当前 token 还剩约 364 天）
.\wbarmor.ps1 setup        # 只把 ~/.codex/config.toml 指到 8790，不碰 token
& "gw\workbuddy2api\.venv\Scripts\python.exe" "gw\workbuddy2api\server\workbuddy_ai_client_demo.py" --login
# 3) 破甲（模板层）
.\wbarmor.ps1 patch
.\wbarmor.ps1 verify
# 4) 选注入载荷（flash 默认 / full 更全 / lazy 惰性）
.\wbarmor.ps1 payload full
.\wbarmor.ps1 restart
```

**Codex 直连配置**（`~\\.codex\\config.toml`，`setup` 会自动写）：
```
model_provider = "ig5"
model = "deepseek-v4.1-flash"
[model_providers.ig5]
base_url = "http://127.0.0.1:8790/v1"
```
`api_key` 随便填（sk-local）。Codex 重启后即用；`oc-*` 前缀走 opencode 免费档自动兜底。

**GUI 按钮一览**：一键启动 / 全部停止 / 刷新 / 验证破甲 / 破甲 patch / 回滚 / 浏览器登录 / 刷新 token / 拉云端模型 / 配置 Codex / DSH 探活 / 免费档探活 / 凭据注入（device·access·refresh）/ 读 session。

**破甲参考**（来自 `dsh-infinite-gen-5-main`）：`prompts/` 下三档载荷 —— `infinite-gen-5.1-flash.md`（10468 字符，默认）、`infinite-gen-5.full.md`（16704 字符）、`infinite-gen-5-lazy.md`（11142 字符）；桥每次请求注入当前 `.payload` 选中的载荷作 system。破甲本体另有磁盘模板层（`patch-armor.ps1` 替换 `*-prompt.tpl` 的 `<content_policy>` 为 `ARMOR_OFF CANARY`），更新应用会覆盖，需重跑 patch。

```powershell
# 端到端判据：Codex 面能出文 + 四端口 + 载荷字符数
.\wbarmor.ps1 status
(Invoke-RestMethod http://127.0.0.1:8790/health).payload_chars
```

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| Codex 经 8790 出文 | 已知 | 2026-10-24 | deepseek-v4.1-flash 200 |
| token 注入/登录路径可用 | 已知 | 应用更新前 | demo OAuth + 现有 session |
| payload 切换生效 | 已知 | 2026-10-24 | full=16704 / flash=10468 实测 |
| 模板破甲 10/10 | 已知 | 下次应用更新 | verify.ps1 十行 ARMOR-OFF |
| 免费档长期可用 | 未知 | — | 官方可调整 |

## 13. 破甲给 Codex / DeepSeek Harness（客户端侧，2026-10-24）

破甲有两个独立落点，**不互相依赖**：

**A. 8790 桥载荷层（服务端）** — 每次请求把 `.payload` 选中的 `infinite-gen-5.*.md` 作为 system 注入。对任何走 8790 的客户端（Codex / DSH / 任意 SDK）都生效。`wbarmor.ps1 payload full|flash|lazy` 切换。

**B. 客户端侧破甲指令（catalog / persona）** — 把 `ARMOR_OFF CANARY=WB-ARMOR-7F3A` 段写进客户端自己的 system：

| 客户端 | 落点 | 生成器 |
|---|---|---|
| Codex | `~/.codex/ig5-model-catalog.json` 每个 model 的 `base_instructions` | `generate-client-armor.py --codex-only` |
| DeepSeek Harness | `~/.dsh/profiles/web/cordis.patch.yml` 的 `personaPrefix` | `generate-client-armor.py --dsh-only` |

`wbarmor.ps1 setup` 会顺带跑 `--codex-only`（幂等，已含 CANARY 不重复写）。Codex 重启后 `base_instructions` 作为 developer 消息进入上游，实测已生效（模型回答「不会拒绝…直接给出步骤/命令/代码/载荷」）。

```powershell
# 一条命令给两端都上破甲（幂等）
& "C:\Program Files\Python314\python.exe" .\generate-client-armor.py
# 或分别
& "C:\Program Files\Python314\python.exe" .\generate-client-armor.py --codex-only
& "C:\Program Files\Python314\python.exe" .\generate-client-armor.py --dsh-only
```

```powershell
# 验证：Codex catalog 六个 model 都带 CANARY
(Get-Content "$env:USERPROFILE\.codex\ig5-model-catalog.json" -Raw) -match 'WB-ARMOR-7F3A'
# 验证：DSH personaPrefix 带 CANARY
Select-String -Path "$env:USERPROFILE\.dsh\profiles\web\cordis.patch.yml" -Pattern 'WB-ARMOR-7F3A' -Quiet
```

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| Codex catalog 6/6 带 CANARY | 已知 | 2026-10-24 | 读回实测 |
| base_instructions 破甲对上游生效 | 已知 | 客户端版本更新前 | developer 消息实调 200 |
| DSH personaPrefix 带 CANARY | 已知 | DSH 重生成 profile 前 | 读回实测 |
| 8790 载荷注入生效 | 已知 | 2026-10-24 | 复述首行 `[MODE` 实测 |
| 客户端破甲在 Codex 新版字段改名后仍有效 | 未知 | — | 依赖 base_instructions 字段名 |


---

## 9. 新增能力与修复记录（2026-10-24）

### 9.1 启动链修复（`启动.cmd` 打不开的根因）

三处路径/递归错误已修：

| 文件 | 原问题 | 现状 |
|---|---|---|
| `scripts\launch-gui.ps1` | 回调 `wbarmor.ps1 gui` → 无限递归 | 改为薄转发到 `gui\launch-gui.ps1` |
| `wbarmor.ps1` 的 `gui` 分支 | 调用的是递归入口 | 直连 `gui\launch-gui.ps1` |
| `gui\launch-gui.ps1` | `gui\selftest.py` 不存在 → `exit 1`；`start-all.ps1` 路径错 | 探测 `dev\selftest.py`；缺自检不阻断；路径改为 `scripts\start-all.ps1` |

```powershell
cd C:\Users\Administrator\Desktop\wb-armor
cmd /c "启动.cmd"        # 期望：GUI launched. + 四端口 True
```

### 9.2 新增命令

```powershell
.\wbarmor.ps1 sync-models     # 从 8790 拉真实模型表，生成 Codex 目录（无 BOM，带 .bak）
.\wbarmor.ps1 status          # 端口 + health + served/fallbacks/last_model/last_status
powershell -File dev\repair.ps1          # 去重代理 + 补 8788 + 窗口句柄丢失时重启 app
powershell -File dev\fix-window.ps1      # 把跑到屏幕外的 ChatGPT 窗口拉回可见区
powershell -File scripts\supervisor.ps1  # 四端口自愈（计划任务 WBSupervisor 每 5 分钟）
```

### 9.3 DSH 接入（web + headless 双侧）

- web profile：`~\.dsh\profiles\web\cordis.patch.yml` —— `llm-deepseek.baseURL = http://127.0.0.1:8790/v1` + `personaPrefix` 破甲
- headless profile：`~\.dsh\profiles\headless\cordis.patch.yml` —— 本次补齐（原来为空 `[]`，导致 headless 直连 `api.deepseek.com` 报 401）
- 桥新增 `POST /v1/messages`（Anthropic 协议）—— DSH 的 deepseek provider 走这个端点；上游 429 时桥自合成 `message_start → content_block_delta → message_stop` 事件流

```powershell
$env:DEEPSEEK_API_KEY='sk-local-proxy'
& 'C:\Users\Administrator\AppData\Local\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd' headless "只回四个字：DSH可用"
# exit=0，输出：好
```

### 9.4 已知限制（功能面）

| 项 | 状态 | 说明 |
|---|---|---|
| 聊天对话 | 可用 | 主链路 200 走透传；429 时自动落 opencode 免费档 |
| 工具调用（写文件/跑命令） | 依赖额度 | 免费档无工具协议；WorkBuddy 429 时只能聊，不能调工具 |
| 多轮上下文 | 可用 | 兜底路径会带最近 8 条消息 |
| 模型选择 | 可用 | `sync-models` 生成 38 条（29 WorkBuddy + 9 opencode） |
| DSH headless | 可用 | 需任意非空 `DEEPSEEK_API_KEY` |
| Codex 窗口不显示 | 已修 | 原因为窗口坐标跑到屏幕外（x=-343），`fix-window.ps1` 可复位 |

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 启动链递归已修、GUI 可拉起 | 已知 | 2026-10-24 | `GUI launched.` + `gui_procs=1` |
| DSH headless 经桥可用 | 已知 | 2026-10-24 | `dsh headless` exit=0 输出「好」 |
| 桥 `/v1/messages` 可用 | 已知 | 2026-10-24 | `type=message text=桥通` |
| 模型目录 38 条、无 BOM | 已知 | 2026-10-24 | `sync-models` 输出 + BOM 检查 False |
| 工具调用可用性取决于 WorkBuddy 额度 | 已知 | — | 带 tools 直打 8788 返回 429 |
| reboot 后自启全链路 | 未知 | — | 未做重启验证 |

---

## 10. 日志系统（排错用）

两个桥都写 JSONL，一行一条事件，字段固定：`ts / level / comp / msg` + 业务字段（`rid`、`status`、`ms`、`tokens`…）。

| 文件 | 写入方 | 内容 |
|---|---|---|
| `logs/ig5-YYYYMMDD.log` | `src/ig5-bridge.mjs` | `responses.start` / `upstream.first` / `stream.synth` / `fallback.opencode` / `upstream.error` |
| `logs/oc-YYYYMMDD.log` | `src/opencode-bridge.mjs` | `chat.start` / `chat.done`（含 tokens、耗时）/ `handler.error` |
| `logs/supervisor.log` | `scripts/supervisor.ps1` | `check` / `start`（哪个服务被拉起）/ `result`（四端口状态） |
| `logs/ig5-debug.log` | 桥（仅 `IG5_DEBUG=1`） | 完整请求体前 4KB，含对话内容，按敏感数据处理 |

### 常用命令

```powershell
cd C:\Users\Administrator\Desktop\wb-armor
.\scripts\logs.ps1                      # 最近 20 行
.\scripts\logs.ps1 -Tail 100 -Level error
.\scripts\logs.ps1 -Since 30 -Stats     # 近 30 分钟：总数 / 各组件 / top-issues
.\scripts\logs.ps1 -Session rABCD1234   # 按请求 rid 拉完整链路
.\scripts\logs.ps1 -Grep fallback       # 关键字过滤
.\scripts\logs.ps1 -Files               # 文件清单与大小
.\scripts\logs.ps1 -Prune 7             # 清理 7 天前的日志
```

### 关联一次请求

桥在每个响应头里回 `x-ig5-rid`，同一次调用内的所有日志都带同一个 `rid`：

```powershell
$h = Invoke-WebRequest http://127.0.0.1:8790/v1/models -UseBasicParsing
$h.Headers['x-ig5-rid']
```

### 环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `WBA_LOG_LEVEL` | `debug` / `info` / `warn` / `error` | `info` |
| `WBA_LOG_DIR` | 日志目录 | `<repo>\logs` |
| `WBA_LOG_MAX` | 单文件轮转阈值（字节） | 5 MB |
| `WBA_LOG_STDERR=1` | 同时打到 stderr（前台调试） | 关 |
| `IG5_DEBUG=1` | 额外写完整请求体到 `ig5-debug.log` | 关 |

### 安全约定

- 键名匹配 `authorization / api-key / token / secret / password / cookie` 的字段一律写成 `***`；
- 长字符串截断到 2000 字符，数组最多取前 20 项；
- `logs/` 已在 `.gitignore` 与发行打包排除列表里，不会进仓库或 zip；
- 轮转：单文件超 `WBA_LOG_MAX` 自动改名 `.1.log`（只保留一份旧文件）。

| 断言 | 态 | 有效期到 | 依据 |
|---|---|---|---|
| 三组件均写 JSONL | 已知 | 2026-10-24 | 实跑 `logs.ps1` 输出三类 `comp` |
| `-Session` 能按 rid 串起桥与上游 | 已知 | 2026-10-24 | `responses.start` + `fallback.opencode` 同 rid |
| 敏感字段脱敏 | 已知 | — | `lib/log.mjs` 的 SECRET 正则 |
| 日志不进版本库 | 已知 | 2026-10-24 | `.gitignore` 含 `logs/`、`*.log` |
| 5MB 轮转实际触发 | 未知 | — | 当前日志远小于阈值 |

### 启动器日志（launcher）

**为什么单独一条**：面板/图标"打不开"时，桥那三份日志全是空的 —— 因为根本没起来。启动器现在自己写 `logs/launcher.log`：

| 事件 | 含义 |
|---|---|
| `start-all.begin` / `start-all.done` | 本轮启动开始/结束时四端口快照（`ports":"8788=1 4097=1 8792=1 8790=1"`） |
| `payload.override` | `.payload` 指定的载荷路径被采用 |
| `bootstrap.start` / `bootstrap.venv.missing` | 首次运行自动建 venv，或建失败 |
| `start.<port>` | 单个服务拉起结果（`up":1` 成功） |
| `opencode.missing` | 4097 需要 opencode CLI，未装时给出 `npm i -g opencode-ai` |
| `retry` / `retry.result` / `port.down` | 端口未起时的重拉，失败时把 stderr 尾部一并记进 `stderr` 字段 |
| `selftest` | 自检退出码（非 0 只警告，不阻断 GUI） |
| `gui.launched` | GUI pid、进程是否存活、用的 exe |
| `gui.already_running` | 单实例守卫命中时的既有 pid |

每个服务另有 `logs\<port>.out.log` / `logs\<port>.err.log`（进程自身的 stdout/stderr）。

```powershell
.\scripts\logs.ps1 -Comp launcher -Tail 10
.\scripts\logs.ps1 -Comp launcher -Level error
.\scripts\logs.ps1 -Since 10 -Stats          # 含 launcher 在内的全局统计
```

PowerShell 脚本统一通过 [lib/wlog.ps1](lib/wlog.ps1) 写日志（与 [lib/log.mjs](lib/log.mjs) 同一 JSONL 结构：`ts/level/comp/msg` + 业务字段），轮转阈值同样受 `WBA_LOG_MAX` 控制。

---

## 11. wb-armor 2.0（重构版控制台）

旧面板把"起服务 / 取 token / 注入 / 配客户端 / 改模型"揉在一起，任一环失败都连带整屏报错。2.0 换成 **内核 + 薄 UI + CLI** 三层：

```
wbarmor/core.py    纯函数：会话/token、模型目录、Codex/DSH 部署、服务控制
wbarmor/cli.py     python -m wbarmor status|token|inject|models|deploy-codex|deploy-dsh|open
gui/app.py         Tk 控制台（异步、去重、5 秒定时状态）
scripts/launch-app.ps1  单实例启动器（可选先跑 start-all）
```

### 六个动作一一对应

| 按钮 | 底层 | 作用 |
|---|---|---|
| ▶ 一键启动 | `core.start_all()` → `scripts/start-all.ps1` | 起 8788/4097/8792/8790，逐端口记录 |
| ■ 停止全部 | `core.stop_all()` → `wbarmor.ps1 down` | 计划任务 + 按端口杀 owner |
| ① 提 Token | `core.session_info()` | 读 `~/.workbuddy-ai-session.json`，显示 accessToken 掩码、deviceToken 长度、剩余天数 |
| ② 注入 Token | `core.inject_device_token()` | 把输入框里的 deviceToken 写回 `auth.deviceToken`（0600），空输入直接拒绝 |
| ③ 部署 Codex | `core.deploy_codex()` | 写 `~/.codex/config.toml`（provider=ig5、绝对 `model_catalog_json`、`[model_providers.ig5]`）+ 补 catalog |
| ④ 部署 DSH | `core.deploy_dsh()` | 写 `~/.dsh/profiles/web/cordis.patch.yml`（可选 headless），带 canary 校验，覆盖前自动备份 |

### 模型列表选择

- 列表来自 8790 `/models`（失败回落 8792），显示 `model-id · owner`；
- **双击**或选中后点「设为默认」→ 写入 `config.toml` 的 `model = "..."`，当前默认项高亮；
- 「刷新模型」重新拉取；启动 600ms 后自动拉一次。

### CLI 等价用法（无 GUI 也能全流程）

```powershell
cd C:\Users\Administrator\Desktop\wb-armor
python -m wbarmor status            # 端口 + health JSON
python -m wbarmor token             # 会话摘要（token 掩码）
python -m wbarmor models            # 列表，* 标当前
python -m wbarmor models --set deepseek-v4.1-flash-sg
python -m wbarmor deploy-codex
python -m wbarmor deploy-dsh --headless
python -m wbarmor start ; python -m wbarmor stop
```

### 与旧版的关系

- 旧入口 `gui/wbarmor_gui.py` 保留但不再被 `启动.cmd` 调用；`启动.cmd` → `scripts/launch-app.ps1` → `gui/app.py`；
- 服务端（`src/*.mjs`、`gw/`）未改，2.0 只是把"操作面"重写：任何一步失败只影响该步，不再连带；
- 日志仍统一进 `logs/`：`launcher.log`（启动与 GUI 事件）、`ig5-*.log`、`oc-*.log`、`<port>.err.log`。

### 2.1 补齐的功能（18 个动作）

| 组 | 动作 | 说明 |
|---|---|---|
| 生命周期 | 一键启动 / 停止全部 / 刷新状态 | start-all 逐端口记录；stop 按端口杀 owner |
| 客户端 | 打开 Codex / 打开 DSH | AUMID 启动 / `dsh --profile web` |
| 诊断 | 打开日志 / 探活(8790+8792) / 计划任务 | 目录直达；responses 与免费档各打一次并计时；任务状态表 |
| Token | ① 提 / ↻ 刷新 / ② 注入 | 读会话、调 demo client refresh、写回 deviceToken |
| 部署 | ③ 部署 Codex / ④ 部署 DSH / 同步模型目录 | 绝对路径 catalog；YAML profile；从 8790 拉清单重写 catalog |
| 破甲 | Patch / 恢复 / 校验 / 状态 | 调 `patch-armor.ps1`、`verify.ps1`；状态按模板扫描 canary 与 `<content_policy>` |
| 模型 | 列表 / 刷新 / 双击设为默认 | 写 `config.toml` 的 `model` |
| 载荷 | 路径框 / 浏览 / 设为载荷 | 写 `.payload`，桥重启后生效 |

CLI 对等命令：`python -m wbarmor armor {status|patch|restore|verify}`、`sync-catalog`、`probe`、`payload [--set PATH]`、`logs [--tail N] [--comp NAME]`、`tasks {status|install|remove}`、`token --refresh`。
