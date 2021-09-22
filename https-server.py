# To generate server certificate:
#   $ openssl req -x509 -nodes -sha256 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 3650
# To start server: (choose your own port number)
#   $ python3 https-server.py <port> --cert cert.pem --key key.pem
# Use Firefox to browse the page, explicitly specify "https://", and click on "Accept the Risk"
# For curl, add --insecure flag to bypass the certificate check

import argparse, ssl, os
from http.server import (HTTPServer, ThreadingHTTPServer,
                         SimpleHTTPRequestHandler, CGIHTTPRequestHandler)

parser = argparse.ArgumentParser()
parser.add_argument('port', type=int)
parser.add_argument('--bind', action='store', required=False, default='0.0.0.0')
parser.add_argument('--dir', action='store', required=False, default=os.getcwd())
parser.add_argument('--key', action='store', required=True, metavar='keyfile')
parser.add_argument('--cert', action='store', required=True, metavar='certfile')
parser.add_argument('--threaded', action='store_true')
parser.add_argument('--cgi', action='store_true')
args = parser.parse_args()

port = args.port
bindaddr = args.bind
rootdir = args.dir
key = os.path.abspath(args.key)
cert = os.path.abspath(args.cert)
threaded = args.threaded
cgi = args.cgi

os.chdir(rootdir)

servercls = ThreadingHTTPServer if threaded else HTTPServer
handlercls = CGIHTTPRequestHandler if cgi else SimpleHTTPRequestHandler
if cgi:
    handlercls.have_fork = False    # force the use of a subprocess

server = servercls((bindaddr, port), handlercls)
with ssl.wrap_socket(server.socket, server_side=True, certfile=cert, keyfile=key) as ssock:
    server.socket = ssock
    server.serve_forever()
