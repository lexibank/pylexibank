# coding: utf8
from __future__ import unicode_literals, print_function, division

import traceback

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from termcolor import colored

from clldutils.clilib import command

from pylexibank.commands.util import with_dataset, _load, _unload
from pylexibank.commands.analyze import analyze
from pylexibank.commands.report import report
from pylexibank.dataset import Dataset


commands = {
    'quit': lambda args: None,
    'download': lambda args: with_dataset(args, Dataset._download),
    'convert': lambda args: with_dataset(args, Dataset._install),
    'analyze': lambda args: with_dataset(args, analyze),
    'report': lambda args: with_dataset(args, report),
    'load': lambda args: with_dataset(args, _load),
    'unload': lambda args: with_dataset(args, _unload),
    'orthography': lambda args: None,
    'help': lambda args: print("Available Commands: %s" % ", ".join(sorted(commands))),
}


def fuzzyfinder(infix, choices):  # pragma: no cover
    return [c for c in choices if infix in c]


@command()
def curate(args):  # pragma: no cover
    datasets = {ds.id: ds for ds in args.datasets}

    class TheCompleter(Completer):
        def get_completions(self, document, complete_event):
            word_before_cursor = document.get_word_before_cursor(WORD=True)
            words = document.text_before_cursor.split()
            if words and words[0] in commands:
                for ds in fuzzyfinder(word_before_cursor, datasets):
                    yield Completion(ds, start_position=-len(word_before_cursor))
            else:  # elif word_before_cursor:
                for c in fuzzyfinder(word_before_cursor, commands):
                    yield Completion(c, start_position=-len(word_before_cursor))

    user_input = []
    while not user_input or user_input[0] != 'quit':
        try:
            user_input = prompt(
                u'lexibank-curator> ',
                history=FileHistory('history.txt'),
                auto_suggest=AutoSuggestFromHistory(),
                completer=TheCompleter(),
            ).split()
        except EOFError:
            break

        if len(user_input) == 0:
            continue  # ignore empty commands
        if user_input[0] not in commands:
            print(colored('Invalid command!', 'red'))
            continue

        args.args = user_input[1:]
        try:
            commands[user_input[0]](args)
        except Exception as e:
            traceback.print_exc()
            print(colored('{0}: {1}'.format(e.__class__.__name__, e), 'red'))

    print('see ya!')
