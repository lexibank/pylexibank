# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.clilib import command

from pylexibank.commands.misc import download, install
from pylexibank.commands.analyze import analyze
from pylexibank.commands.report import report


@command()
def sync(args):
    download(args)
    install(args)
    analyze(args)
    report(args)
