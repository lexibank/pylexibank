import argparse

# from clldutils.clilib import command
from nexus import NexusWriter

from pylexibank.commands.util import get_dataset


# FIXME: only register as command, once it is implemented!
# @command()
def nexus(args):  # pragma: no cover
    usage = """
    Convert a lexibank dataset to nexus.

        lexibank nexus <DATASET> --output=...
    """
    get_dataset(args)
    parser = argparse.ArgumentParser(prog='nexus', usage=usage)
    parser.add_argument('--output', help='Nexus output file', default=None)
    xargs = parser.parse_args(args.args[1:])

    writer = NexusWriter()

    if not xargs.output:
        print(writer.write())
    else:
        writer.write_to_file(filename=xargs.output)
