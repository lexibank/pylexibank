"""
Connect to the database with sqlite3.
"""
import subprocess

import termcolor

from pylexibank.cli_util import add_db
from pylexibank.db import Database


def register(parser):
    add_db(parser)


def run(args):
    db = str(Database(args.db).fname)
    args.log.info('connecting to {0}'.format(termcolor.colored(db, 'green')))
    subprocess.check_call(['sqlite3', db])
