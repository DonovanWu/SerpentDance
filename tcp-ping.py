import time, socket, argparse, atexit, math


def mean(arr):
    if len(arr) == 0:
        return float('nan')
    return sum(arr) / len(arr)


def std(arr):
    if len(arr) == 0:
        return float('nan')
    elif len(arr) == 1:
        return 0.
    
    avg = mean(arr)
    return math.sqrt(sum(map(lambda x: (x - avg) ** 2, arr)) / len(arr))


def display_stats():
    if len(stats) > 0:
        print('\n--- %s ping statistics ---' % host)
        print('round-trip min/avg/max/stddev = %.3f/%.3f/%.3f/%.3f ms' % (
                min(stats), mean(stats), max(stats), std(stats)))


parser = argparse.ArgumentParser()
parser.add_argument('host')
parser.add_argument('-p', action='store', type=int, required=False, default=80, metavar='port',
                    help="Server's port to connect to for testing ping. Default is 80.")
parser.add_argument('-c', action='store', type=int, required=False, default=4, metavar='count')
parser.add_argument('-w', action='store', type=float, required=False, default=2, metavar='timeout')
args = parser.parse_args()

host = args.host
port = args.p
count = args.c
timeout = args.w

ip = socket.gethostbyname(host)

atexit.register(display_stats)

stats = []
print('Using TCP connection to probe RTT: %s:%d' % (ip, port))
for i in range(count):
    try:
        try:
            sock = socket.socket()
            sock.settimeout(timeout)
            start = time.time()
            sock.connect((host, port))
            dura = (time.time() - start) * 1000
            print('Received SYN-ACK from %s: count=%d, time=%.3fms' % (ip, i, dura))
            stats.append(dura)
        except ConnectionRefusedError:
            print('Connection refused by %s:%d' % (ip, port))
            break
        except socket.timeout:
            print('Connection timed out for count=%d' % i)
            continue
        finally:
            sock.close()
        time.sleep(1)
    except KeyboardInterrupt:
        break
