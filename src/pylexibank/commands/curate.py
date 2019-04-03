from time import time
import traceback

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from termcolor import colored
from appdirs import user_data_dir
from clldutils.path import Path
from clldutils.clilib import command

from pylexibank.util import aligned
from pylexibank.commands.util import with_dataset, _load, _unload
from pylexibank.dataset import Dataset


commands = {
    'quit': lambda args: None,
    'download': lambda args: with_dataset(args, Dataset._download),
    'makecldf': lambda args: with_dataset(args, Dataset._install),
    'dbload': lambda args: with_dataset(args, _load),
    'dbunload': lambda args: with_dataset(args, _unload),
    'orthography': lambda args: None,
    'help': lambda args: print("Available Commands: \n%s" % aligned(
        [(k, getattr(v, '__doc__', '')) for k, v in sorted(commands.items())])),
}
commands['quit'].__doc__ = ': exits lexibank curator'
commands['download'].__doc__ = "<dataset> : run <dataset>'s download method"
commands['makecldf'].__doc__ = "<dataset> : create CLDF for <dataset>"
commands['dbload'].__doc__ = "<dataset> : load an installed dataset into the SQLite DB"
commands['dbunload'].__doc__ = "<dataset> : drop an installed dataset from the SQLite DB"


def fuzzyfinder(infix, choices):  # pragma: no cover
    return [c for c in choices if infix in c]


@command()
def curate(args):  # pragma: no cover
    datasets = {ds.id: ds for ds in args.cfg.datasets}

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
    appdir = Path(user_data_dir('lexibank'))
    if not appdir.exists():
        appdir.mkdir(parents=True)

    while not user_input or user_input[0] != 'quit':
        try:
            user_input = prompt(
                u'lexibank-curator> ',
                history=FileHistory(str(appdir / 'history.txt')),
                auto_suggest=AutoSuggestFromHistory(),
                completer=TheCompleter(),
            ).split()
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if len(user_input) == 0:
            continue  # ignore empty commands
        if user_input[0] not in commands:
            print(colored('Invalid command!', 'red'))
            continue
        if len(user_input) > 1 and user_input[1] not in datasets:
            print(colored('Invalid dataset!', 'red'))
            continue

        args.args = user_input[1:]
        try:
            s = time()
            commands[user_input[0]](args)
            print('[{0:.3f}]'.format(time() - s))
        except Exception as e:
            traceback.print_exc()
            print(colored('{0}: {1}'.format(e.__class__.__name__, e), 'red'))

    print('see ya!')
