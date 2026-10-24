# 已发布

- 仓库：https://github.com/Bailan766/wb-armor （private，默认分支 `main`）
- 本地仓库已 push，历史自包含；`gw/workbuddy2api` 以上游 submodule 引用（`Zhengyuuuui/workbuddy2api`），`vendor/dsh-infinite-gen-5/` 内置三档载荷。

## 之后如何更新
```powershell
# 修改后
git add -A
git commit -m "描述"
git push origin main
```

## 若换机器/克隆
```powershell
git clone --recurse-submodules https://github.com/Bailan766/wb-armor.git
# 首次运行：先装 Python 3 / Node / opencode，再
.\wbarmor.ps1 gui
```

## 敏感项
`.gitignore` 排除 `*.session.json` / `.payload` / `ig5-debug.log` / `logs/` / `.venv/`。不要把这些提交上来。
