# apocalypse
ddos dos tool tools/ISTRUZIONI DEL TOOL LEGGI ATTENTAMENTE (OBBLIGATORIO): ISTRUZIONI DEL TOOL: fate il download di TUTTI I FILE metteteli in una cartella esempio nome cartella: APOCALYPSE, e aprite su linux/windows/mac il file gui_apocalypse.py e dopo avrete il programma apocalypse. nella CASELLA dove bisogna selezionare l'ip o l'url non usare IP, il TOOL funziona solo con URL. IMPOSTA IL PAYLOAD A 10KB altrimenti potrebbe compromettere il funzionamento. ApocalypseDOS è uno strumento DDoS (con GUI) scritto in Python, ATTENZIONE QUESTO TOOL PUO ESSRE CONSIDERATO ANCHE SUPERIORE A LOIC. E SOPRATUTO CON Solo scopi informativi.


# APOCALYPSE-DDOS 🔥

![Logo](skull.jpg)

**APOCALYPSE-DDOS** è il tool definitivo per test di stress e simulazione DDoS, con oltre 30+ metodi Layer 4/7: potente, veloce e facile da usare.  
> ⚡️ **Usalo solo per scopi educativi e test autorizzati!** ⚡️

---

## ⭐️ Caratteristiche principali

- **30+ metodi DDoS Layer 4 & Layer 7** (inclusi GET, POST, OVH, STRESS, TCP, UDP, SYN, NTP, DNS, etc)
- **Gestione proxy avanzata** (HTTP, SOCKS4, SOCKS5, random)
- **Bypass cloudflare/antiddos** (CFB, DGB, BOMB, etc)
- **Interfaccia grafica (GUI) facile** con 3 console parallele
- **Configurabile da file o da GUI** (target, thread, proxies e altro)
- **Performance e multithreading** al massimo livello
- **Console Tools**: info, ping, check, dstat, ecc (solo modalità CLI)

---

## 🚀 Installazione

**1. Clona il repository**
```bash
git clone https://github.com/valerio213/apocalypse-ddos.git
cd apocalypse-ddos
```

**2. Installa Python 3.8+**

Assicurati di avere Python 3.8 o superiore:
```bash
python3 --version
```

**3. Installa le dipendenze**
```bash
pip install -r requirements.txt
```
Se ti serve la GUI:  
```bash
pip install pillow requests
```

**4. (Opzionale) Scarica proxylist**
- Puoi usare le proxylist già incluse o personalizzarne una in `files/proxies/`.

---

## 🛠️ Esecuzione di dos.py

```bash
python3 dos.py <metodo> <target/url/ip:port> <socks_type> <threads> <proxylist> <rpc> <durata>
```
**Esempi:**
- Layer7:  
  `python3 dos.py GET http://example.com 1 2000 http.txt 64 60`
- Layer4:  
  `python3 dos.py TCP 1.2.3.4:80 1000 60`
- Amplification:  
  `python3 dos.py NTP 1.2.3.4:80 1000 60 ntp_reflectors.txt`
- Tools:  
  `python3 dos.py TOOLS`

**Avvia GUI (se vuoi la grafica):**
```bash
python3 gui_apocalypse.py
```

---

## 📦 Cosa bisogna installare per dos.py?

- **Python >= 3.8**
- Tutte le librerie in `requirements.txt`  
  (PyRoxy, cloudscraper, requests, Pillow, psutil, yarl, icmplib, impacket, ecc)
- Consigliato:  
  ```
  pip install -r requirements.txt
  pip install pillow requests
  ```
- (Opzionale) [bombardier](https://github.com/codesenberg/bombardier) se vuoi usare il metodo BOMB.

---

## 🧑‍💻 Come contribuire?

- Fai una fork, crea una branch, proponi una pull-request!
- Metti una ⭐️ se il progetto ti piace!
- Scrivi issue per bug, suggerimenti o nuove feature!

---

## ⚠️ Disclaimer

Questo tool è **solo per test legali ed educativi** su infrastrutture di TUA proprietà o con autorizzazione scritta.  
**Non usare per scopi malevoli. L’autore declina ogni responsabilità.**

---

## ⭐️ Dai una stella e condividi!

Se ti piace APOCALYPSE-DDOS, lascia una ⭐️ e condividilo nei tuoi gruppi, social, forum!  
Più siamo, più funzionalità aggiungeremo!

---

### Seguici & Community

- Telegram: [Gruppo ufficiale](https://t.me/tuo-gruppo)
- Youtube: [Demo video](https://www.youtube.com/results?search_query=apocalypse+ddos)
- Issues & Pull Request sempre benvenute!

---
