"""wb-armor single-file launcher -> open GUI."""
import os, sys
ROOT = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI = os.path.join(ROOT, "gui", "wbarmor_gui.py")
PY = r"C:\Program Files\Python314\python.exe"
LOG = os.path.join(ROOT, "launcher.log")

def log(m):
    try: open(LOG, "a", encoding="utf-8").write(m + "\n")
    except: pass

def main():
    log("start ROOT=%s GUI_exists=%s" % (ROOT, os.path.exists(GUI)))
    if not os.path.exists(GUI):
        try:
            import tkinter as tk; from tkinter import messagebox
            r = tk.Tk(); r.withdraw(); messagebox.showerror("wb-armor", "找不到 gui\\wbarmor_gui.py，请把 exe 放到仓库根目录。"); r.destroy()
        except Exception: pass
        return 1
    ps1 = os.path.join(ROOT, "wbarmor.ps1")
    try:
        import subprocess
        subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",ps1,"up"],
                       cwd=ROOT, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("up done")
    except Exception as e:
        log("up err %s" % e)
    try:
        import subprocess
        subprocess.Popen([PY, GUI], cwd=ROOT, close_fds=True)
        log("gui spawned")
    except Exception as e:
        log("gui err %s" % e)
        try:
            import tkinter as tk; from tkinter import messagebox
            r = tk.Tk(); r.withdraw(); messagebox.showerror("wb-armor", "启动 GUI 失败:\n%s" % e); r.destroy()
        except Exception: pass
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
