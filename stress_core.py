import asyncio
import aiohttp
import time
import random
import argparse
import ssl
import certifi # Per ottenere il percorso del bundle di CA fidate
from collections import deque
import sys
import json
import socket # Per getaddrinfo nella risoluzione DNS standard
import dns.resolver # Per risoluzione DNS avanzata (dnspython)
import numpy as np # Per calcoli statistici
from urllib.parse import urlparse
import logging
import ctypes # Per ottimizzazione priorità su Windows

# --- Setup del Logging ---
# Configura il logger all'inizio per catturare tutti i messaggi
logging.basicConfig(
    level=logging.INFO, # Default a INFO, cambiabile con --log-level
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Ottimizzazione del Sistema (Richiede sudo su Linux/Crostini) ---
try:
    if sys.platform.startswith('win'):
        # Aumenta la priorità del processo su Windows
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)  # HIGH_PRIORITY_CLASS
        logger.info("Priorità del processo impostata su ALTA (Windows).")
    else:
        # Aumenta il limite di file aperti su Linux/macOS
        import resource
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_limit = 1000000 # Un milione di file aperti, un valore molto alto
        if new_limit > hard_limit:
            new_limit = hard_limit # Non superare il limite massimo del sistema
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard_limit))
        logger.info(f"Limite di file aperti impostato a {new_limit} (Linux/macOS).")
except Exception as e:
    logger.warning(f"Ottimizzazione sistema fallita (potrebbe richiedere 'sudo'): {e}")

# --- CLI Arguments ---
parser = argparse.ArgumentParser(description='HTTP/HTTPS High-Performance Load Tester (Ethical Use Only)')
parser.add_argument('target', type=str, help='URL target (es. https://example.com/path)')
parser.add_argument('-d', '--duration', type=int, default=60, help='Durata test in secondi (default: 60)')
parser.add_argument('-c', '--concurrency', type=int, default=2000, help='Massimo richieste concorrenti (default: 2000)')
parser.add_argument('-t', '--timeout', type=float, default=8.0, help='Timeout per singola richiesta in secondi (default: 8.0)')
parser.add_argument('--method', type=str, default='GET', choices=['GET', 'POST', 'HEAD', 'OPTIONS'], help='Metodo HTTP (default: GET)')
parser.add_argument('--data', type=str, help='Dati per richieste POST/PUT (es. \'{"key":"value"}\')')
parser.add_argument('--headers', type=str, help='Header HTTP aggiuntivi in formato JSON (es. \'{"X-Custom":"Value"}\')')
parser.add_argument('--payload-size', type=str, help='Dimensione del payload per richieste POST/PUT (es. "10KB", "1MB", "500B"). Sovrascrive --data.') # NUOVO ARGOMENTO
parser.add_argument('--keepalive', action='store_true', help='Mantieni connessioni HTTP attive tra le richieste (default: false, disabilitato per massimizzare la concorrenza su nuove connessioni)')
parser.add_argument('--dns-refresh', type=int, default=60, help='Frequenza di aggiornamento DNS in secondi (0 per disabilitare, default: 60)')
parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Livello di logging (default: INFO)')
parser.add_argument('--no-ssl-verify', action='store_true', help='Disabilita la verifica del certificato SSL (ATTENZIONE: meno sicuro)')
args = parser.parse_args()

# Aggiorna il livello di logging dopo aver parsato gli argomenti
logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

# --- Variabili Globali per Statistiche e Lock ---
stats = {
    'total': 0, 'success': 0, 'failed': 0,
    'status_codes': {}, 'errors': {},
    'latencies': deque(maxlen=20000), # Aumentato per maggiore precisione
    'start_time': time.perf_counter(),
    'last_dns_refresh': 0,
    'lock': asyncio.Lock(), # Un singolo lock per tutte le statistiche
    'active_connections': 0 # Variabile per monitorare connessioni attive
}

# --- Risoluzione DNS Dinamica e Load Balancing DNS ---
async def resolve_dns(hostname):
    # La risoluzione DNS avverrà in un thread separato per non bloccare l'event loop
    try:
        # Usa dns.resolver per un controllo più fine e load balancing (se ci sono più IP)
        answers = await asyncio.get_event_loop().run_in_executor(
            None, # Usa il thread pool predefinito
            lambda: dns.resolver.resolve(hostname, 'A')
        )
        ip_addresses = [str(a) for a in answers]
        if not ip_addresses:
            raise ValueError(f"No IP addresses found for {hostname}")
        # Ritorna un IP casuale per bilanciare il carico DNS
        return random.choice(ip_addresses)
    except dns.resolver.NXDOMAIN:
        logger.error(f"DNS resolution failed: Domain '{hostname}' not found (NXDOMAIN).")
        return None
    except dns.resolver.NoAnswer:
        logger.error(f"DNS resolution failed: No A record found for '{hostname}'.")
        return None
    except Exception as e:
        logger.error(f"DNS resolution error for '{hostname}': {e}")
        return None

# --- Configurazione SSL Ottimizzata ---
def create_ssl_context_for_aiohttp():
    if args.no_ssl_verify:
        return False # Aiohttp accetta False per disabilitare la verifica
    
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2 # TLS 1.2 o superiore è il minimo raccomandato
    ctx.set_ciphers('ECDHE+AESGCM:CHACHA20:DHE+AESGCM:!RC4') # Cifre moderne preferite
    ctx.options |= ssl.OP_NO_COMPRESSION | ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 # Disabilita compressione e vecchi SSL/TLS
    # ctx.check_hostname = True # Abilitato di default con create_default_context e cafile

    return ctx

# --- Generazione Header HTTP ---
# Modificato per accettare la dimensione del payload generato
def generate_headers(method, custom_headers_json, payload_size_bytes=0):
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            f'PyStressTester/{random.randint(1, 9)}.{random.randint(0, 9)}' # User-Agent personalizzato
        ]),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'it-IT,it;q=0.9', 'fr-FR,fr;q=0.9', 'de-DE,de;q=0.9']),
        'Connection': 'keep-alive' if args.keepalive else 'close', # Controllo dinamico Keep-Alive
        'Referer': f"{urlparse(args.target).scheme}://{urlparse(args.target).hostname}/" # Aggiungi Referer
    }

    if method in ['POST', 'PUT']:
        if payload_size_bytes > 0:
            headers['Content-Type'] = 'application/octet-stream' # Tipo generico per dati binari
            headers['Content-Length'] = str(payload_size_bytes) # Specifica la dimensione del payload
        elif args.data:
            # Tenta di inferire il Content-Type se i dati sono JSON
            try:
                json.loads(args.data)
                headers['Content-Type'] = 'application/json'
            except json.JSONDecodeError:
                headers['Content-Type'] = 'application/x-www-form-urlencoded' # Fallback
            
    if custom_headers_json:
        try:
            parsed_headers = json.loads(custom_headers_json)
            headers.update(parsed_headers)
        except json.JSONDecodeError:
            logger.warning(f"Header personalizzati non validi, ignorati: {custom_headers_json}. Richiesto formato JSON.")
    return headers

# --- La Coroutine del Worker ad Alta Velocità ---
async def http_worker(session, target_url_base, method, payload, headers, semaphore, ssl_context):
    global stats
    
    # Pre-parse dell'URL target per ottenere hostname e path per la risoluzione DNS e request path
    parsed_url = urlparse(args.target)
    hostname = parsed_url.hostname
    
    # Il percorso da aggiungere all'IP risolto (es. /path/to/resource)
    request_path = parsed_url.path if parsed_url.path else '/'
    if parsed_url.query:
        request_path += '?' + parsed_url.query

    while True: # Il worker continua a inviare richieste finché non viene cancellato
        current_time = time.perf_counter()
        
        # Risoluzione DNS dinamica (se abilitata e necessario)
        if args.dns_refresh > 0 and current_time - stats['last_dns_refresh'] > args.dns_refresh:
            async with stats['lock']:
                stats['last_dns_refresh'] = current_time # Aggiorna il timestamp dell'ultimo refresh DNS
            
            resolved_ip = await resolve_dns(hostname)
            if resolved_ip:
                # Ricostruisci l'URL per usare l'IP risolto direttamente, bypassando il DNS di aiohttp per la prossima richiesta
                # Questo evita che aiohttp cache il DNS a lungo se use_dns_cache=False
                target_url_effective = f"{parsed_url.scheme}://{resolved_ip}:{parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)}{request_path}"
                # logger.debug(f"DNS refreshed for {hostname} -> {resolved_ip}")
            else:
                # Se la risoluzione DNS fallisce, riprova con l'hostname originale come fallback
                target_url_effective = args.target # Usa l'URL originale
                logger.debug(f"Using original target URL due to DNS resolution failure for {hostname}")
        else:
            # Se DNS refresh è disabilitato o non è il momento, usa l'URL originale
            target_url_effective = args.target

        async with semaphore: # Limita il numero di richieste HTTP/S concorrenti
            start_req_time = time.perf_counter()
            try:
                async with session.request(
                    method,
                    target_url_effective, # Usa l'URL potenzialmente risolto
                    headers=headers,
                    data=payload,
                    ssl=ssl_context, # Passa il contesto SSL configurato
                    allow_redirects=False # Disabilita i redirect per ridurre il carico sul client
                ) as response:
                    # Leggi il minimo necessario per chiudere la connessione e ottenere il codice di stato
                    # Puoi commentare await response.read() se vuoi solo l'header e il codice di stato per massimizzare la velocità
                    # ma potrebbe lasciare connessioni pendenti sul server se non legge il corpo.
                    await response.read()  

                    latency = time.perf_counter() - start_req_time
                    
                    async with stats['lock']:
                        stats['total'] += 1
                        stats['latencies'].append(latency)
                        status = response.status
                        stats['status_codes'][status] = stats['status_codes'].get(status, 0) + 1
                        
                        if 200 <= status < 400: # Successo se 2xx o 3xx (senza redirect)
                            stats['success'] += 1
                        else:
                            stats['failed'] += 1
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                latency = time.perf_counter() - start_req_time # Calcola latenza anche in caso di errore
                async with stats['lock']:
                    stats['total'] += 1
                    stats['failed'] += 1
                    stats['latencies'].append(latency) # Aggiungi latenza anche per errori
                    err_type = type(e).__name__
                    stats['errors'][err_type] = stats['errors'].get(err_type, 0) + 1
                logger.debug(f"Request failed: {err_type} - {e}") # Log solo a livello DEBUG per non inondare
            except Exception as e: # Cattura altri errori imprevisti
                latency = time.perf_counter() - start_req_time
                async with stats['lock']:
                    stats['total'] += 1
                    stats['failed'] += 1
                    stats['latencies'].append(latency)
                    err_type = type(e).__name__
                    stats['errors'][err_type] = stats['errors'].get(err_type, 0) + 1
                logger.error(f"Unexpected error in worker: {err_type} - {e}")
            
            # Nessun sleep qui per massimizzare il throughput. I/O Bound.

# --- Monitoraggio in Tempo Reale ---
async def live_monitor():
    global stats
    
    # Intestazione iniziale per il monitor
    print(f"\n{'='*80}\n{'Live Monitoring':^80}\n{'='*80}")
    print(f"{'Time (s)':<10} | {'Requests':<10} | {'RPS':<8} | {'Success%':<8} | {'Failed':<8} | {'Latency Avg (ms)':<18}")
    print(f"{'-'*80}")

    while True:
        await asyncio.sleep(1) # Aggiorna ogni secondo
        elapsed = time.perf_counter() - stats['start_time']
        
        async with stats['lock']:
            total = stats['total']
            success = stats['success']
            failed = stats['failed']
            latencies_copy = list(stats['latencies']) # Copia per evitare modifiche durante il calcolo

        rps = total / elapsed if elapsed > 0 else 0
        success_rate = (success / total * 100) if total > 0 else 0
        avg_latency_ms = (np.mean(latencies_copy) * 1000) if latencies_copy else 0

        # Aggiorna la stessa riga della console
        sys.stdout.write(
            f"\r{int(elapsed):<10} | {total:<10} | {rps:<8.1f} | {success_rate:<8.1f} | {failed:<8} | {avg_latency_ms:<18.2f}"
        )
        sys.stdout.flush()

# --- Funzione per interpretare la dimensione del payload ---
def parse_payload_size(size_str):
    if not size_str:
        return 0

    size_str = size_str.strip().upper()
    if size_str.endswith('MB'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('KB'):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith('B'):
        return int(float(size_str[:-1]))
    else:
        # Assumi che sia in byte se non specificato
        return int(float(size_str))


# --- Inizializzazione Test Principale ---
async def run_test():
    global stats

    # Pre-elaborazione dell'URL target
    parsed_url = urlparse(args.target)
    if not parsed_url.scheme or not parsed_url.hostname:
        logger.error("URL target non valido. Assicurati che includa schema (http/https) e hostname.")
        sys.exit(1)

    target_hostname = parsed_url.hostname
    
    # Risoluzione DNS iniziale (blocking call, ma avviene solo una volta all'inizio)
    # È cruciale che questo funzioni per la prima richiesta
    initial_ip = await resolve_dns(target_hostname)
    if not initial_ip:
        logger.error(f"Impossibile risolvere il DNS per {target_hostname}. Il test non può iniziare.")
        sys.exit(1)
    
    target_base_url_for_requests = args.target # Usiamo l'URL originale per compatibilità SSL e comodità

    # Prepara payload per POST/PUT
    payload_data = None
    payload_description = "N/A"

    if args.payload_size:
        payload_size_bytes = parse_payload_size(args.payload_size)
        if payload_size_bytes > 0:
            payload_data = b'A' * payload_size_bytes
            payload_description = f"{payload_size_bytes / (1024*1024):.2f} MB" if payload_size_bytes >= (1024*1024) else \
                                  f"{payload_size_bytes / 1024:.2f} KB" if payload_size_bytes >= 1024 else \
                                  f"{payload_size_bytes} Bytes"
            logger.info(f"Ogni richiesta POST/PUT invierà un payload di {payload_description}.")
            if args.data:
                logger.warning("Il parametro --data è stato ignorato perché è stato specificato --payload-size.")
        else:
            logger.warning("La dimensione del payload specificata è 0 o non valida, nessun payload generato.")
    elif args.data:
        try:
            payload_data = args.data.encode('utf-8')
            payload_description = f"{len(payload_data)} Bytes (da --data)"
        except Exception as e:
            logger.error(f"Errore nella codifica dei dati payload: {e}. Assicurati che i dati siano una stringa valida.")
            sys.exit(1)
    
    # Genera gli header una volta sola, passando la dimensione del payload se presente
    request_headers = generate_headers(args.method, args.headers, len(payload_data) if payload_data else 0)
    
    # Configura il contesto SSL
    ssl_context = create_ssl_context_for_aiohttp()

    # Configurazione del connector TCP di aiohttp
    # limit=0 significa nessun limite sul numero totale di connessioni TCP,
    # il limite è gestito dal semaphore aiohttp.ClientSession.
    # limit_per_host per limitare connessioni per singolo host.
    connector = aiohttp.TCPConnector(
        limit=0, # Nessun limite a livello di connector, il semaphore lo gestirà
        limit_per_host=args.concurrency, # Limita connessioni per singolo host
        ssl=ssl_context,
        enable_cleanup_closed=True,
        # Se keepalive è True, il timeout è elevato. Altrimenti è 0 per chiusura immediata.
        keepalive_timeout=65 if args.keepalive else 0,
        # force_close=not args.keepalive, # Non più necessario con keepalive_timeout=0
        use_dns_cache=False, # Disabilita la cache DNS interna di aiohttp
        ttl_dns_cache=0 # Insieme a use_dns_cache=False, garantisce nessun caching DNS di aiohttp
    )
    
    timeout_settings = aiohttp.ClientTimeout(total=args.timeout)
    # Il semaphore controlla il numero massimo di richieste HTTP/S in volo (concorrenti)
    semaphore = asyncio.Semaphore(args.concurrency)
    
    # Inizializza la sessione aiohttp
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout_settings,
        auto_decompress=True # Permette ad aiohttp di decomprimere automaticamente le risposte gzip/deflate
    ) as session:
        logger.info(f"🚀 AVVIO TEST SU {args.target} | DURATA: {args.duration}s | CONCORRENZA: {args.concurrency}")
        logger.info(f"  Metodo: {args.method} | Keep-Alive: {args.keepalive} | SSL Verify: {not args.no_ssl_verify}")
        if payload_data and (args.method == 'POST' or args.method == 'PUT'):
            logger.info(f"  Dimensione Payload per richiesta: {payload_description}")
        elif args.method in ['POST', 'PUT']:
             logger.info(f"  Nessun payload specificato per richieste {args.method}.")
        
        # Avvio dei worker. Creiamo un numero maggiore di worker rispetto alla concorrenza
        # per assicurarci che il semaphore sia sempre impegnato e che il pool di richieste
        # non si esaurisca mai.
        num_workers = args.concurrency * 2 # Ogni worker tenta di inviare una richiesta
        workers = [
            asyncio.create_task(http_worker(session, target_base_url_for_requests, args.method, payload_data, request_headers, semaphore, ssl_context))
            for _ in range(num_workers)
        ]
        monitor_task = asyncio.create_task(live_monitor())
        
        # Aspetta la durata specificata
        await asyncio.sleep(args.duration)
        
        logger.info("\nTest di stress terminato. Cancellazione delle task rimanenti...")
        
        # Terminazione controllata dei worker e del monitor
        for task in workers:
            task.cancel()
        monitor_task.cancel()
        
        # Attendi che tutte le task siano terminate (gestendo le CancellationError)
        await asyncio.gather(*workers, return_exceptions=True)
        await asyncio.gather(monitor_task, return_exceptions=True)
        
        # Chiudi il connector solo dopo che tutte le sessioni e i task lo hanno rilasciato
        await connector.close()
        logger.info("Tutte le task sono state cancellate e il connettore chiuso.")

# --- Report Finale ---
def generate_report():
    elapsed = time.perf_counter() - stats['start_time']
    # Evita divisione per zero se elapsed è molto piccolo
    rps = stats['total'] / elapsed if elapsed > 0 else 0
    
    print("\n\n" + "="*80)
    print(f"⚡ TEST COMPLETATO IN {elapsed:.2f} SECONDI")
    print("="*80)
    print(f"🔗 Target: {args.target}")
    print(f"📈 Richieste Totali: {stats['total']}")
    print(f"📊 Throughput: {rps:.2f} richieste/secondo (RPS)")
    print(f"✅ Successi: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "N/A")
    print(f"🔴 Falliti: {stats['failed']}")
    
    print("\n📊 Codici di Stato HTTP:")
    if stats['status_codes']:
        for code, count in sorted(stats['status_codes'].items()):
            print(f"  Status {code}: {count} richieste")
    else:
        print("  Nessun codice di stato registrato.")
            
    print("\n⚠️ Errori Riscontrati:")
    if stats['errors']:
        for err, count in stats['errors'].items():
            print(f"  {err}: {count}")
    else:
        print("  Nessun errore di connessione/timeout registrato.")
            
    if stats['latencies']:
        latencies = np.array(list(stats['latencies'])) # Converti deque in array numpy
        if latencies.size > 0:
            print("\n⏱️ Tempi di Risposta (ms):")
            print(f"  Min: {latencies.min()*1000:.2f} | Max: {latencies.max()*1000:.2f}")
            print(f"  Media: {latencies.mean()*1000:.2f} | Mediana (P50): {np.percentile(latencies, 50)*1000:.2f}")
            print(f"  P90: {np.percentile(latencies, 90)*1000:.2f} | P95: {np.percentile(latencies, 95)*1000:.2f} | P99: {np.percentile(latencies, 99)*1000:.2f}")
        else:
            print("\n⏱️ Nessun tempo di risposta registrato.")
    print("="*80)

if __name__ == "__main__":
    # Comando di esecuzione su Crostini:
    # pip install aiohttp certifi dnspython numpy
    # sudo python3 il_tuo_script.py https://example.com -c 3000 -d 60 --log-level INFO --payload-size 10MB

    print("\n" + "="*80)
    print("       🚀 HTTP/HTTPS High-Performance Load Tester        ")
    print("        (Uso Etico e Responsabile RICHIESTO)             ")
    print("="*80)
    print(f"Target: {args.target}")
    print(f"Durata: {args.duration}s | Concorrenza: {args.concurrency}")
    print(f"Timeout: {args.timeout}s | Metodo: {args.method}")
    print(f"Dati: {args.data or 'N/A'} | Header: {args.headers or 'N/A'}")
    print(f"Payload Size: {args.payload_size or 'N/A'}") # Aggiunto il payload size all'output iniziale
    print(f"Keep-Alive: {args.keepalive} | DNS Refresh: {args.dns_refresh}s | SSL Verify: {not args.no_ssl_verify}")
    print("-" * 80)
    print("Preparazione test... Si prega di attendere.")

    try:
        asyncio.run(run_test())
        generate_report()
    except KeyboardInterrupt:
        logger.info("\nTest interrotto manualmente dall'utente. Generazione del report...")
        generate_report()
    except Exception as e:
        logger.critical(f"\nUn errore critico ha interrotto il test: {e}", exc_info=True)
        generate_report() # Prova a generare un report parziale