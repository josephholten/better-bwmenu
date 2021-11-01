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
    # if unauthenticated or locked you need the password

    # password = run_cmd(['rofi', '-dmenu', '-p', 'Master Password', '-password', '-lines' ,'0'])
    # password = password.rstrip('\n')
    password = '7N"}g<wux,?w2]fS'
    output = None

    if status['status'] == 'unauthenticated':
        # code = subprocess.run(['rofi', '-dmenu','-p', 'YubiKey 2FA code', '-password', '-lines' ,'0'], capture_output=True, text=True).stdout.rstrip("\n")
        code = input("Provide 2FA: ")
        output = subprocess.run(['bw', 'login', 'joseph@holten.com', password, '--method', '3', '--code', code], capture_output=True, text=True)
        
        if not output.stdout.startswith('You are logged in!'):   # failed at logging in
            print("Error logging in: ", output, file=sys.stderr)
            exit(1)

    if status['status'] == 'locked':
        output = subprocess.run(["keyctl", "request", "user", "bw_session"])

        if output.stderr == '' and output.stdout.rstrip("\n").isdigit():  # session key available
            key_id = output.stdout.rstrip("\n")
            output = subprocess.run(["keyctl", "print", key_id], capture_output=True, text=True)
            session_key = output.stdout.rstrip("\n")

        if output.stderr == 'request_key: Required key not available':  # session auto locked
            output = subprocess.run(["bw", "unlock", password]) 

    else:
        assert false, "Unhandled status"

    session_key = extract_session_key(output.stdout)

    output = subprocess.run(["keyctl", "add", "user", "bw_session", session_key, "@u"], capture_output=True, text=True)
    key_id = output.stdout.rstrip("\n")
    output = subprocess.run(["keyctl", "timeout", key_id, AUTO_LOCK], capture_output=True, text=True)

            
            



# MAIN PART




# try to reschedule the logout
output = subprocess.run(["keyctl", "request", "user", "bw_logout"])
if output.stdout.rstrip("\n").isdigit():  # have gotten a key_id
    # remove pending logout
    key_id = output.stdout.rstrip("\n")
    output = subprocess.run(["keyctl", "print", key_id], capture_output=True, text=True)
    job_id = output.stdout.rstrip("\n")

    output = subprocess.run(["atrm", job_id], capture_output=True, text=True)

    if output.stderr or output.stdout:
        print("Error rescheduling 'bw logout': invalid jobid.\nkeyctl error message: ", output, file=sys.stderr)
        exit(1)

if not output.stdout.rstrip("\n").isdigit() or output.stderr != "request_key: Required key not available":  # some error, that is not that the job has already been performed
    print("Error rescheduling 'bw logout': couldn't get job_id from keyctl.\nkeyctl error message: ", output, file=sys.stderr)
    exit(1)

# schedule new logout
output = os.popen(f'echo "bw logout" | at now + {AUTO_LOGOUT} minutes')
job_id = output.readline().rstrip("\n")
output = subprocess.run(["keyctl", "add", "user", "bw_logout", job_id, "@u"], capture_output=True, text=True)
output = subprocess.run(["keyctl", "timeout", AUTO_LOGOUT*60], capture_output=True, text=True)


