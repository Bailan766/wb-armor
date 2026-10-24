"""wb-armor 双击启动器：
1) 自定位仓库根
2) 后台静默起四进程（wbarmor.ps1 up）
3) 打开 GUI 控制台（pythonw 无黑窗）
"""
import os, sys

def _detect_root():
    exe_dir = os.path.dirname(sys.executable)
    cands = []
    if getattr(sys, "frozen", False):
        cands += [exe_dir, os.path.dirname(exe_dir), os.getcwd()]
    else:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands += [here, os.getcwd()]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "gui", "wbarmor_gui.py")):
            return c
    return cands[0] if cands else exe_dir

ROOT = _detect_root()
GUI = os.path.join(ROOT, "gui", "wbarmor_gui.py")
PS1 = os.path.join(ROOT, "wbarmor.ps1")
CANDIDATES = [
    os.path.join(ROOT, "gw", "workbuddy2api", ".venv", "Scripts", "pythonw.exe"),
    os.path.join(ROOT, "gw", "workbuddy2api", ".venv", "Scripts", "python.exe"),
    sys.executable,
    r"C:\Program Files\Python314\pythonw.exe",
    r"C:\Program Files\Python314\python.exe",
]

def pick():
    for c in CANDIDATES:
        if c and os.path.exists(c):
            return c
    import shutil
    return shutil.which("pythonw") or shutil.which("python")

def main():
    if not os.path.exists(GUI):
        _msg("找不到 gui\\wbarmor_gui.py\n请把 wb-armor.exe 放在仓库根目录。")
        return 1
    import subprocess
    if os.path.exists(PS1):
        try:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1, "up"],
                           cwd=ROOT, timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=0x08000000)
        except Exception:
            pass
    py = pick()
    if not py:
        _msg("未找到 Python 3.10+。")
        return 1
    env = dict(os.environ); env["WBARMOR_ROOT"] = ROOT
    subprocess.Popen([py, GUI], cwd=ROOT, close_fds=True, env=env,
                     creationflags=0x08000000 if py.lower().endswith("python.exe") else 0)
    return 0

def _msg(m):
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk(); r.withdraw(); messagebox.showerror("wb-armor", m); r.destroy()
    except Exception:
        sys.stderr.write(m + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
