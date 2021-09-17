import argparse, threading, itertools, math, sys
import subprocess, platform, shlex
from ipaddress import IPv4Address, IPv4Network

MAX_THREADS = 64
ping_config = {
    'fast': {
        'count': 1,
        'wait': 1,
    },
    'private': {
        'count': 2,
        'wait': 1,
    },
    'public': {
        'count': 4,
        'wait': 1,
    },
    'slow': {
        'count': 6,
        'wait': 2,
    },
}
lock = threading.Lock()


def chunks(l, n):
    c = itertools.count()
    return [list(it) for _, it in itertools.groupby(l, lambda x: next(c) // n)]


def ping(ipaddr):
    system = platform.system()
    if system == 'Windows':
        ping_config[config_choice]['wait'] *= 1000    # to milliseconds
        cmd = 'ping /n %(count)d /w %(wait)d' % ping_config[config_choice]
    elif system == 'Darwin':
        cmd = 'ping -c %(count)d -W %(wait)d' % ping_config[config_choice]
    elif system == 'Linux':
        cmd = 'ping -c %(count)d -W %(wait)d' % ping_config[config_choice]
    else:
        raise RuntimeError('Unknown platform: %s' % system)
    cmd = shlex.split(cmd) + [ipaddr]
    
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        with lock:
            print(ipaddr)


parser = argparse.ArgumentParser(description="Parallelized ping sweep. Prints hosts that are up to stdout.")
parser.add_argument('cidr', nargs='?', help="If not given, please pass an input file of IP addresses, "
                                            "one per line, to the stdin.")
parser.add_argument('-t', action='store', type=int, required=False, default=4, metavar='num_threads',
                    help="Number of threads. Must be between 1 and %d (inclusively). Default is 4." % MAX_THREADS)
parser.add_argument('-c', action='store', required=False, default='private', choices=list(ping_config),
                    help="Choose a ping configuration. Sweeps faster when in lower-latency, less-lossy networks.")
args = parser.parse_args()

cidr = args.cidr
num_threads = args.t
config_choice = args.c

if not 1 <= num_threads <= MAX_THREADS:
    raise ValueError('Number of threads must be between 1 and %d inclusively.' % MAX_THREADS)

if cidr is None:
    if sys.stdin.isatty():
        print('Please enter a list of IP addresses, one per line, ending by EOF (Ctrl + D on Unix-like systems):')
    all_hosts = []
    for line in sys.stdin.readlines():
        line = line.strip()
        if line == '':
            continue
        all_hosts.append(line)
    if sys.stdin.isatty():
        print('Scanning for hosts that are up...')
else:
    net = IPv4Network(cidr)
    if net.num_addresses == 1:
        all_hosts = [net.network_address]
    elif net.num_addresses > 1:
        all_hosts = list(map(str, net.hosts()))
    else:
        raise ValueError("This shouldn't happen.")

ip_chunks = chunks(all_hosts, math.ceil(len(all_hosts) / num_threads))

workers = []
for i in range(len(ip_chunks)):
    task = threading.Thread(target=lambda iplist: list(map(ping, iplist)), args=(ip_chunks[i], ))
    workers.append(task)

for task in workers:
    task.start()

for task in workers:
    task.join()
