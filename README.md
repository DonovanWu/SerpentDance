Serpent Dance
========

## Overview

Serpent Dance is a collection of simple Python scripts for security testing. You may also find it useful in CTFs or pentest exams. If that is the case, please give credit to the original author (e.g. by providing link to this repository).

The name of this project is inspired by a scene in Blade Runner, because... Python penetration testing??

Also, please don't mind some "decorative" stuff I added to the scripts... It's to give the scripts some more "identity", more or less like the useless "mother fXXker" entry in Mirai's list of default credentials. LOL

## Scripts

All scripts are intended to be run with Python 3. Python 2 will not work.

### packet-blackhole.py

This is basically a netcat (nc) server, but with logging and daemonizing capabilities. It can be used as a very basic honey pot.

No external Python package needs to be installed to run this script.

### secure-reverse-shell.py

This is basically an `ncat` client and requires user to provide a server ceritificate, so that the reverse shell transmission can be encrypted. If you don't want to install suspicious programs on a client's machine, but the client's machine has `python3` installed, you can simply use this script.

Notice that by default all your operations on your Ncat server will be printed on the screen of the client, who executes the script to send you the reverse shell. This is done because we assume your use of this script is benign, and giving the client side some feedback can lead to less confusion and more trust.

Notice that this reverse shell script is intended for Unix-like systems (e.g. Linux, Mac OS, etc.).

No external Python package needs to be installed to run this script.

### tcp-ping.py

A script to test round-trip time (RTT) for hosts that don't answer ping (e.g. those that have a firewall that blocks ICMP) by using TCP handshake, provided that you know what port is open on the host. Notice that TCP protocol has packet retransmission mechanism, so this script cannot measure packet loss rate, and RTT can blow up when severe packet loss occurs. Therefore, this script shall only be used as a desperate measure.

No external Python package needs to be installed to run this script.

### pingsweep.py

A script to perform a parallelized ping sweep. You can either provide a network range in CIDR format (pass as an argument) or a file containing a list of IP addresses to ping (pass to stdin).

When testing in a private network environment, I noticed the more threads I used, the more false negative I tend to get (i.e. replies not received from hosts that are actually up). Same thing seem to happen to `nmap -sn` and `arp-scan` and I do not know the reason. If you have insights on what might have caused this, please let me know by all means. As for now, I'm setting the default number of threads to 4 for a balance between accuracy and speed (which is a bit on the slow side).

This script requires `ipaddress` (version `>=1.0.23`).

### https-server.py

Pretty much Python 3's HTTP server in `http` module (i.e. `python3 -m http.server <port>`) but encrypts the traffic. If the pentest is done via public network, this script might be useful when transferring files.

Most likely, you'll need to bypass certificate checking on the client side:
* For `curl` users, add the flag `--insecure`
* For Firefox users, click on "Advanced..." button and then choose "Accept the Risk and Continue"
* For Chrome users, it seems like you have to generate a self-signed CA to sign your certificate, and then add the CA to Trusted Root Certification Authorities, which is too much work to do, so I suggest using Firefox instead

If you encounter something like a "connection reset" error in your browser, make sure you have explicitly specified `https://` protocol.

No external Python package needs to be installed to run this script.

### pyinstaller-make.py

I encountered a few situations where I needed to turn a python script into an executable when learning about pentest so I wrote this script. Under the hood it uses `pyinstaller`. It includes two subcommands `install` and `clean`. Hopefully it makes compiling python scripts into executables easier for you.

Currently it's under active development, and still needs some testing and debugging.

This script requires `pip` (latest version) and `konsoru` (version `>=0.1.2`).
