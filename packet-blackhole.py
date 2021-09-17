import os, sys, time, atexit, inspect, json, binascii
import argparse, socket, select, platform, random
import traceback as tb
import logging, logging.config, logging.handlers
import chardet


def hexdump(data):
    lines = []
    while len(data) > 0:
        chunk = data[:16]
        data = data[16:]

        fmt = ['%02x'] * len(chunk)
        if len(fmt) > 8:
            fmt.insert(8, '')
        fmt = ' '.join(fmt)

        readable = ''.join(chr(b) if 0x20 <= b <= 0x7e else '.' for b in chunk)

        line = '%-48s    %s' % (fmt % tuple(chunk), readable)
        lines.append(line)
    return '\n'.join(lines)


# ----------------------------------------
# Parse arguments
# ----------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument('addrport', nargs='?', default='0.0.0.0:80',
                    help='Optional port number, or ipaddr:port; defaults to 0.0.0.0:80')
parser.add_argument('--max_clients', action='store', type=int, default=10, required=False)
parser.add_argument('--log', action='store', default=None, required=False,
                    help="Name of log file. No logging if not provided.")
parser.add_argument('--daemon', action='store_true')
parser.add_argument('--banner', action='store', default=None, required=False,
                    help="If specified, send a banner upon client connection. Servers such as smtp, ssh, pop3 all do this.")
parser.add_argument('--minimalist', action='store_true',
                    help="Minimalist logging format, making it even closer to a netcat server.")
args = parser.parse_args()

addrport = args.addrport.split(':')
if len(addrport) == 1:
    server_ip = '0.0.0.0'
    portno = int(addrport[0])
elif len(addrport) == 2:
    server_ip, portno = addrport[0], int(addrport[1])
else:
    raise ValueError('Incorrect addrport format!')
max_clients = args.max_clients
logfile = args.log
daemon = args.daemon
banner = args.banner
minimalist = args.minimalist

# ----------------------------------------
# Initialize logging
# ----------------------------------------

logconfig = {
    'version': 1,
    'formatters': {
        'standard': {
            'format': "%(asctime)s.%(msecs)03d {} %(levelname)s: %(message)s".format(__file__),
            'datefmt': "%Y-%m-%d %H:%M:%S",
        },
        'minimalist': {
            'format': "%(message)s",
            'datefmt': "%Y-%m-%d %H:%M:%S",
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard' if not minimalist else 'minimalist',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
if logfile:
    logconfig['handlers']['logfile'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': logfile,
        'maxBytes': 10e6,
        'formatter': 'standard' if not minimalist else 'minimalist',
    }
    logconfig['loggers']['']['handlers'].append('logfile')
if daemon:
    if not logfile:
        raise ValueError('Must specify a log file to run in daemon mode!')
    logconfig['loggers']['']['handlers'].remove('console')
logging.config.dictConfig(logconfig)

# ----------------------------------------
# Preprocess banner
# ----------------------------------------

if banner is not None:
    banner += '\r\n'
    banner = banner.encode()


# ----------------------------------------
# Utilities
# ----------------------------------------

class ConnectionInfo:
    def __init__(self, ip, port, ttl=60):
        self.ip = ip
        self.port = port
        self.ttl = ttl
        self._default_ttl = ttl

    def reset_ttl(self):
        self.ttl = self._default_ttl


# ----------------------------------------
# Primary functions
# ----------------------------------------

def tcp():
    # creates a TCP socket
    master_sock = socket.socket()

    # allow others to reuse the address
    master_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # build server's internet address
    master_sock.bind((server_ip, portno))

    # listen to client connections
    master_sock.listen(max_clients)

    # server loop
    logging.info("TCP server initialized: host = %s port = %d.\n" % (server_ip, portno))
    read_fd_set = [master_sock]
    conn_info = {}
    while True:
        tick = time.time()
        rlist, wlist, xlist = select.select(read_fd_set, [], [], 10)
        for fd in rlist:
            if fd is master_sock:
                # new connection
                sock, addr_info = fd.accept()
                hostaddr, port = addr_info
                logging.info("Host '%s' connected via port %d" % (hostaddr, port))
                sock.setblocking(0)
                read_fd_set.append(sock)
                conn_info[sock] = ConnectionInfo(hostaddr, port)
                if isinstance(banner, bytes):
                    # randon delay up to 3 seconds to create a sense of server overload / slow network
                    time.sleep(random.random() * 3)
                    sock.send(banner)
            else:
                # data arriving on existing connections
                try:
                    data = fd.recv(65536)
                    if data:
                        # received data
                        logging.info('Received data from connection: %s:%d' % (conn_info[fd].ip, conn_info[fd].port))
                        guess = chardet.detect(data)
                        if guess['encoding'] is not None:
                            if guess['confidence'] < 0.5:
                                logging.debug(
                                    'Low encoding detection confidence: %.4f. Decoding anyway...' % guess['confidence'])
                            try:
                                data = data.decode(guess['encoding'])
                            except UnicodeDecodeError:
                                data = hexdump(data)
                        else:
                            data = hexdump(data)
                        logging.info('Data received:\n%s' % data)
                        conn_info[fd].reset_ttl()
                    else:
                        # connection closed
                        if fd in conn_info:
                            logging.info('Connection closed: %s:%d' % (conn_info[fd].ip, conn_info[fd].port))
                        else:
                            logging.info('Socket closed: %d' % fd.fileno())
                        fd.close()
                        read_fd_set.remove(fd)
                        if fd in conn_info:
                            del conn_info[fd]
                except ConnectionResetError:
                    # client sent a TCP reset, which will force this error
                    if fd in conn_info:
                        logging.info('Connection reset from %s:%d' % (conn_info[fd].ip, conn_info[fd].port))
                    else:
                        logging.info('Connection reset on socket %d' % fd.fileno())
                    fd.close()
                    read_fd_set.remove(fd)
                    if fd in conn_info:
                        del conn_info[fd]
                except Exception as e:
                    logging.error(tb.format_exc())

        remove_list = []
        time_passed = time.time() - tick
        for fd in conn_info:
            if fd not in read_fd_set:
                continue
            conn_info[fd].ttl -= time_passed
            if conn_info[fd].ttl <= 0:
                logging.info('Actively closed connection: %s:%d' % (conn_info[fd].ip, conn_info[fd].port))
                fd.close()
                read_fd_set.remove(fd)
                if fd in conn_info:
                    remove_list.append(fd)
        for fd in remove_list:
            del conn_info[fd]


def exit_message():
    if daemon and pid > 0:
        return
    logging.info('Bye bye.')


# ----------------------------------------
# Run program
# ----------------------------------------

atexit.register(exit_message)
main = tcp

if not daemon:
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit
elif platform.system() == 'Windows':
    raise RuntimeError('Sorry, cannot create daemon on Windows!')
else:
    # dual fork hack to make process run as a daemon
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            print('pid:', pid)
            sys.exit(0)
    except OSError as e:
        sys.exit(1)

    main()
