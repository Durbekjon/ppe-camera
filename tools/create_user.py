"""Create a dashboard user or reset their password.

Usage: .venv/bin/python -m tools.create_user NAME --role admin|supervisor
The password is asked for interactively, so it never lands in shell history.
"""
import argparse
import getpass
import sys

from app import auth, db

parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("--role", choices=auth.ROLES, required=True)
args = parser.parse_args()

password = getpass.getpass("Parol: ")
if password != getpass.getpass("Parolni takrorlang: "):
    sys.exit("Parollar mos kelmadi")
db.init()
try:
    auth.set_user(args.username, password, args.role)
except ValueError as e:
    sys.exit(str(e))
print(f"Tayyor: {args.username.strip().lower()} ({args.role})")
