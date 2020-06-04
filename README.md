Serpent Dance
========

## Overview

Serpent Dance is a collection of simple Python scripts for security testing. You may also find it useful in CTFs or pentest exams. If that is the case, please give credit to the original author (e.g. by providing link to this repository).

The name of this project is inspired by a scene in Blade Runner, because... Python penetration testing??

Also, please don't mind some "decorative" stuff I added to the scripts. It's to give the scripts some more "identity", much like the useless "mother fXXker" entry in Mirai's list of default credentials.

## Scripts

All scripts are written with Python 3 in mind. Some parts of their code are not compatible with Python 2.

### packet-blackhole.py

This is basically a netcat (nc) server, but with logging and daemonizing capabilities. It can be used as a very basic honey pot.

No external Python package needs to be installed to run this script.

### secure-reverse-shell.py

This is basically an `ncat` client and requires user to provide a server ceritificate, so that the reverse shell transmission can be encrypted. If you don't want to install `nmap` on a client's machine to run `ncat`, but client's machine has `python3` installed, you can simply use this script.

Notice that by default all your operations on your Ncat server will be printed on the screen of the client, who executes the script to send you the reverse shell. This is done because we assume your use of this script is benign, and giving the client side some feedback can lead to less confusion and more trust.

No external Python package needs to be installed to run this script.

### tcp-ping.py

A script to test round-trip time (RTT) for hosts that don't answer ping (e.g. those that have a firewall that blocks ICMP) by using TCP handshake, if you know what port is open on the host. Notice that TCP protocol has packet retransmission mechanism, so this script cannot measure packet loss rate, and RTT can blow up when severe packet loss occurs.

This script requires `numpy`.

### pingsweep.py

A script to perform a parallelized ping sweep. You can either provide a network range in CIDR format (pass as an argument) or a file containing a list of IP addresses to ping (pass to stdin). When testing in a private network environment, I noticed when more threads are used, I tend to not receive replies from more hosts that are actually up. I do not know the reason. If you have insight on what might have caused this, please let me know by all means. As for now, I'm setting the default number of threads to 4 for a balance between accuracy and speed (which is a bit on the slow side).

This script requires `ipaddress`.
