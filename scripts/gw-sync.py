#!/usr/bin/env python3
"""Sync bundled gw/workbuddy2api with upstream GitHub repo (default Zhengyuuuui/workbuddy2api).

用法：
    python scripts/gw-sync.py            # 只比较（check）
    python scripts/gw-sync.py --apply    # 写入（先自动打包备份）
    python scripts/gw-sync.py --apply --repo owner/name --ref main

依赖：gh CLI 已登录（gh auth token 提供 API 凭据）、能访问 api.github.com。
比较基准是 git blob sha（sha1("blob <len>\\0"+content)），与 git 完全一致；
行尾差异（CRLF/LF）也会被如实报出来。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "gw" / "workbuddy2api"
ARCHIVE = ROOT.parent / "_archive"
SKIP = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", ".git")


def gh_token() -> str:
    out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit("gh CLI 未登录：先执行 gh auth login")
    return out.stdout.strip()


TOKEN = gh_token()


def api(path: str):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "wb-armor-gw-sync"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def local_hashes() -> dict[str, str]:
    out = {}
    for p in LOCAL.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(LOCAL).as_posix()
        if rel.startswith(".venv/") or "/__pycache__/" in "/" + rel or rel.endswith(".pyc"):
            continue
        out[rel] = blob_sha(p.read_bytes())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Zhengyuuuui/workbuddy2api")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--apply", action="store_true", help="写入本地（默认只比较）")
    args = ap.parse_args()

    head = api(f"/repos/{args.repo}/git/ref/heads/{args.ref}")["object"]["sha"]
    tree = api(f"/repos/{args.repo}/git/trees/{head}?recursive=1")
    upstream = {n["path"]: n["sha"] for n in tree["tree"] if n["type"] == "blob"}
    local = local_hashes()

    missing = sorted(set(upstream) - set(local))
    extra = sorted(set(local) - set(upstream))
    changed = sorted(k for k in upstream.keys() & local.keys() if upstream[k] != local[k])

    print(f"upstream {args.repo}@{head[:10]}  files={len(upstream)}")
    print(f"local files={len(local)}  missing={len(missing)} changed={len(changed)} extra={len(extra)}")
    for label, items in (("+ upstream-only", missing), ("~ changed", changed), ("- local-only", extra)):
        for i in items[:10]:
            print(f"  {label}: {i}")

    if not args.apply:
        print("check only（--apply 才会写文件）")
        return 0 if not (missing or changed) else 1

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    stamp = head[:10]
    backup = ARCHIVE / f"workbuddy2api-pre-sync-{stamp}.zip"
    if not backup.exists():
        tmp = ARCHIVE / "_tmp_gw"
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(LOCAL, tmp, ignore=SKIP)
        shutil.make_archive(str(backup.with_suffix("")), "zip", tmp)
        shutil.rmtree(tmp)
        print("backup ->", backup)

    written = 0
    for path, sha in upstream.items():
        dest = LOCAL / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(api(f"/repos/{args.repo}/contents/{path}?ref={args.ref}")["content"])
        if dest.exists() and blob_sha(dest.read_bytes()) == sha:
            continue
        dest.write_bytes(data)
        written += 1
    print("written", written)

    bad = [p for p, s in upstream.items() if not (LOCAL / p).exists() or blob_sha((LOCAL / p).read_bytes()) != s]
    print("verify mismatch", len(bad), bad[:5])
    return 0 if not bad else 2


if __name__ == "__main__":
    raise SystemExit(main())
