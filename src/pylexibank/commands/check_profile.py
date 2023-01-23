"""
Check forms against a dataset's orthography profile.
"""
import re
import collections
from unicodedata import normalize

from cldfbench.cli_util import with_dataset, add_catalog_spec
from clldutils.clilib import Table, add_format
from pylexibank.cli_util import add_dataset_spec


def normalized(string, mode="NFD"):
    return normalize(mode, string)


def register(parser):
    add_format(parser, default="pipe")
    add_dataset_spec(parser)
    add_catalog_spec(parser, "clts")
    parser.add_argument(
        '--language',
        help="Select a language",
        default=None)
    parser.add_argument(
        "--noprofile",
        help="Ignore profile use segments",
        action="store_true",
        default=False)


def codepoints(string):
    return " ".join(["U+" + x.rjust(4, "0") for x in [hex(ord(char))[2:] for char in string]])


def run(args):
    with_dataset(args, check_profile)


def check_profile(dataset, args):
    def n(tk):
        return re.sub('>>$', '', re.sub(r'^<<', '', tk))
    visited = {}
    problems = collections.OrderedDict([
        ('generated', collections.defaultdict(list)),
        ('modified', collections.defaultdict(list)),
        ('slashed', collections.defaultdict(list)),
        ('unknown', collections.defaultdict(list)),
        ('missing', collections.defaultdict(list)),
    ])
    for row in dataset.cldf_dir.read_csv("forms.csv", dicts=True):
        if not args.language or args.language == row["Language_ID"]:
            kw = dict(column="IPA")
            if 'Profile' in row:  # A multi-profile dataset.
                kw['profile'] = row['Profile']
            tokens = [normalized(t) for t in (
                dataset.tokenizer(row, row["Form"], **kw)
                if dataset.tokenizer and not args.noprofile
                else row["Segments"].split()
            )]
            for tk in set(tokens):
                if tk not in visited:
                    sound = args.clts.api.bipa[tk]
                    if tk.startswith("<<") and tk.endswith(">>"):
                        visited[tk] = "missing"
                    elif sound.type == "unknownsound":
                        visited[tk] = "unknown"
                    elif sound.generated:
                        visited[tk] = "generated"
                    elif str(sound) not in {tk, normalized(tk), normalized(tk, mode='NFC')}:
                        if "/" in tk and str(sound) == tk.split('/')[1]:
                            visited[tk] = "slashed"
                        else:
                            visited[tk] = "modified"
                if tk in visited:
                    problems[visited[tk]][n(tk)].append(
                        (" ".join(tokens), row["Form"], row["Graphemes"]))

    with Table(
        args,
        'Category',
        'Grapheme',
        'Grapheme-UC',
        'Non-normal',
        'Diacritics',
        'BIPA',
        "BIPA-UC",
        "Segments",
        "Graphemes",
        "Count",
    ) as table:
        for cat, tokens in problems.items():
            for tk, values in tokens.items():
                table.append([
                    cat,
                    tk,
                    codepoints(tk.split('/')[0] if cat == 'slashed' else tk),
                    "*" if cat == 'generated' and tk != str(args.clts.api.bipa[tk]) else "",
                    "◌" + tk if cat in {'missing', 'unknown'} else '',
                    str(args.clts.api.bipa[tk]),
                    args.clts.api.bipa[tk].codepoints,
                    values[0][0],
                    values[0][1],
                    len(values),
                ])
