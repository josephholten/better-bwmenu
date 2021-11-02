#!/usr/bin/env python3
import sys
import subprocess

print("\0delim\x1f\x03")

if len(sys.argv) > 1:
    if sys.argv[1] == "change":
        prompt = subprocess.run(["rofi", "-dmenu", "-p", "Change prompt to:"], capture_output=True, text=True).stdout
        print(f"\0prompt\x1f{prompt}", end='\x03')
    elif sys.argv[1] == "quit":
        exit(0)
    else:
        print("\0prompt\x1fselect:", end='\x03')
else:
    print("\0prompt\x1fselect:", end='\x03')

print("change\nthe prompt", end='\x03')
print("reload\nthe app", end='\x03')
print("quit", end='\x03')
