# Credits / 引用与致谢

本项目是在下列开源/第三方项目之上做的整合与二次开发。**核心功劳归原作者**，本项目只负责补链路编排、GUI、路由/兜底、破甲注入与文档。

## 直接引用

| 项目 | 作者 | 用途 | 许可 |
|---|---|---|---|
| [Zhengyuuuui/workbuddy2api](https://github.com/Zhengyuuuui/workbuddy2api) | Zhengyuuuui | WorkBuddy/CodeBuddy 的 OpenAI/Responses/Anthropic 兼容反代（`gw/workbuddy2api/` 里以 submodule/拷贝形式引用） | 见上游 LICENSE |
| [SunsetRNE/dsh-infinite-gen-5](https://github.com/SunsetRNE/dsh-infinite-gen-5) | SunsetRNE | 提示词破甲载荷 `infinite-gen-5.*.md` + DSH 插件形态（`prompts/` 载荷引用） | MIT (c) 2026 SunsetRNE |
| [opencode](https://opencode.ai) / [sst/opencode](https://github.com/sst/opencode) | SST | 本地免费档模型 CLI / `serve`，本项目在其上套 OpenAI 兼容壳 `opencode-bridge.mjs` | 见上游 LICENSE |

## 间接依赖

- FastAPI / Uvicorn / httpx / requests（反代运行时）
- Node.js 标准库 `http`（8790 桥、8792 壳，零 npm 依赖）
- Python 标准库 `tkinter`（GUI，无需 pip）
- mitmproxy（可选，仅用于从本地客户端抓 `x-device-token`）

## 说明

- `gw/workbuddy2api/` 是上游项目的拷贝，其 `.git` 与原 remote 保留在上游仓库，本项目不重新托管其历史。改进建议请优先回馈上游。
- 破甲载荷来自 `dsh-infinite-gen-5`，请遵守其 MIT 许可与合规定位（受控环境红队科研/鲁棒性评测）。
- 反代协议（external-link-v2 / `/v3/config` / OAuth state→token）为对官方客户端行为的兼容实现，非官方 SDK。

如你是上述项目的作者并希望调整署名方式，开 issue 即可。
