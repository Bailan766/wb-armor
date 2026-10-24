# 推送到 GitHub（本机已就绪，阻塞项在认证与网络）

本地仓库**已建好并提交完成**（分支 `master`，48 个文件，~250KB，敏感文件已 .gitignore）：
- `git log`：`a7e7fde feat: wb-armor ...`
- 自包含：`vendor/dsh-infinite-gen-5/` 内置三档载荷，`gw/workbuddy2api/` 以上游 git 引用

## 当前阻塞（两个都必须解决）
1. **GitHub 认证失效**：`gh auth status` = `The token in keyring is invalid`（旧 `ghp_…` 已吊销/过期）。
2. **到 github.com:443 连接超时**（`Failed to connect to github.com:443`）。`api.github.com:443` 可达，但 git push 的 `github.com:443` 不通 —— 需要代理或换用能通 443 的网络。

## 恢复后两条命令搞定（在仓库根目录）
```powershell
# A) 重新登录（浏览器，一次即可）
gh auth login -h github.com -w

# B) 建私有仓库并推送（自动命名，或用 --source 绑定）
gh repo create wb-armor --private --source . --remote origin --push
#   若想改为公开： --public
```

不想用 gh 的等价做法：
```powershell
# 先在网页建空仓库 github.com/<you>/wb-armor，然后：
git remote add origin https://github.com/<you>/wb-armor.git
git branch -M main
git push -u origin main
```

## 离线兜底
- 完整历史已打包：`outputs/wb-armor.bundle`
- 到任意联网机器：
  ```powershell
  git clone wb-armor.bundle wb-armor
  cd wb-armor
  git remote add origin https://github.com/<you>/wb-armor.git
  git push -u origin master
  ```

## 推送前已核对
- `.gitignore` 排除：`*.session.json` / `.payload` / `ig5-debug.log` / `logs/` / `.venv/` / 嵌套 `.git`
- 全仓库扫描：无 JWT、无 `v3:` 设备 token、无真实 uid、无邮箱凭据（仅一处 `noreply@anthropic.com` 占位）
