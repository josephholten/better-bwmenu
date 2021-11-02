#!/usr/bin/env python

import sys
import os
import subprocess
import json
from enum import IntEnum
from pprint import pprint

EMAIL = "joseph@holten.com"
method = 3
AUTO_LOCK = 1800
AUTO_LOGOUT = 120   # in minutes

def bw_status():
    return json.loads(subprocess.run(['bw', 'status'], capture_output=True, text=True).stdout)

def extract_session_key(message: str) -> str:
    key_start = message.find('"')
    key_end = message.find('"', key_start+1)
    return message[key_start+1:key_end]

status = bw_status()

session_key = ""

if status['status'] == 'unlocked':
    session_key = os.environ.get('BW_SESSION')

else:
    # try to find session key in keyctl 
    output = subprocess.run(["keyctl", "request", "user", "bw_session"], capture_output=True, text=True)

    # session key available (i.e. defacto unlocked)
    if output.stderr == '' and output.stdout.rstrip("\n").isdigit():  
        key_id = output.stdout.rstrip("\n")
        output = subprocess.run(["keyctl", "print", key_id], capture_output=True, text=True)

        session_key = output.stdout.rstrip("\n")
        
        print("Success getting session_key from keyctl")

    # no session key saved with keyctl (i.e. locked or unauthenticated)
    else:
        # definitely need password
        password = subprocess.run(['rofi', '-dmenu', '-p', 'Master Password', '-password', '-lines' ,'0'], capture_output=True, text=True).stdout
        password = password.rstrip('\n')

        output = None

        if status['status'] == 'unauthenticated':
            code = subprocess.run(['rofi', '-dmenu','-p', 'YubiKey 2FA code', '-password', '-lines' ,'0'], capture_output=True, text=True).stdout.rstrip("\n")
            output = subprocess.run(['bw', 'login', 'joseph@holten.com', password, '--method', '3', '--code', code], capture_output=True, text=True)
            
            if not output.stdout.startswith('You are logged in!'):   # failed at logging in
                print("Error logging in: ", output, file=sys.stderr)
                exit(1)

        elif status['status'] == 'locked':
            output = subprocess.run(["bw", "unlock", password]) 

        else:
            assert False, f"Unhandled status {status}"

        session_key = extract_session_key(output.stdout)


# register session_key with keyctl
output = subprocess.run(["keyctl", "add", "user", "bw_session", session_key, "@u"], capture_output=True, text=True)
key_id = output.stdout.rstrip("\n")
output = subprocess.run(["keyctl", "timeout", key_id, str(AUTO_LOCK)], capture_output=True, text=True)

# deschedule old logout
output = subprocess.run(["keyctl", "request", "user", "bw_logout"], capture_output=True, text=True)
if output.stdout.rstrip("\n").isdigit():  # have gotten a key_id
    # remove pending logout
    key_id = output.stdout.rstrip("\n")
    output = subprocess.run(["keyctl", "print", key_id], capture_output=True, text=True)
    job_id = output.stdout.rstrip("\n")

    output = subprocess.run(["atrm", job_id], capture_output=True, text=True)


elif output.stderr != "request_key: Required key not available\n":  # some error, that is not that the job has already been performed
    print("Error rescheduling 'bw logout': couldn't get job_id from keyctl.\nkeyctl error message: ", output, file=sys.stderr)
    exit(1)
            
# MAIN PART

output = subprocess.run(["bw", "list", "items", "--session", session_key], capture_output=True, text=True)
items = json.loads(output.stdout)

if (sys.argc == 1):   # init call to program
    # list all items by name
    for item in items:
        print(item['name'])   # TODO: with meta search of the url

if (sys.argc == 2):
    name = sys.argv[1]

    identifiers = ['name', 'username', 'url', 'id']
    for id_type in identifiers:
        if duplicates:
            continue
        else:
            for (id in items_by_id_type):
                print(id)
            




output = subprocess.run(f'bw list items --session {session_key}', capture_output=True, text=True, shell=True)

items = json.loads(output.stdout)
pprint(items)

# END MAIN

# schedule new logout
output = subprocess.run(f'echo "bw logout" | at now + {AUTO_LOGOUT} minutes', capture_output=True, text=True, shell=True)
job_id = output.stderr.split("\n")[1].split()[1]
output = subprocess.run(["keyctl", "add", "user", "bw_logout", job_id, "@u"], capture_output=True, text=True)
output = subprocess.run(["keyctl", "timeout", str(AUTO_LOGOUT*60)], capture_output=True, text=True)
