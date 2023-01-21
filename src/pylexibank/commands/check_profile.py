"""
Check forms against a dataset's orthography profile.
"""
import typing
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


def print_problems(args,
                   items,
                   label,
                   with_grapheme_uc: typing.Union[bool, typing.Callable] = False,
                   with_bipa=False,
                   add_item=None):
    if items:
        print("# Found {} {} graphemes".format(len(items), label))
        cols = ["Grapheme"]
        if with_grapheme_uc:
            cols.append('Grapheme-UC')
        if with_bipa:
            cols.append('BIPA')
        if add_item:
            cols.append(add_item[0])
        cols.extend(["BIPA-UC", "Segments", "Graphemes", "Count"])

        with Table(args, *cols) as table:
            for tk, values in sorted(items.items(), key=lambda x: len(x[1])):
                row = [tk]
                if with_grapheme_uc:
                    row.append(
                        with_grapheme_uc(tk) if callable(with_grapheme_uc) else codepoints(tk))
                if with_bipa:
                    row.append(str(args.clts.api.bipa[tk]))
                if add_item:
                    row.append(add_item[1](tk))
                row.extend([
                    args.clts.api.bipa[tk].codepoints,
                    values[0][0],
                    values[0][1],
                    len(values),
                ])
                table.append(row)


def check_profile(dataset, args):
    visited = {}
    missing, unknown, modified, generated, slashed = {}, {}, {}, {}, {}
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
                        missing[tk[2:-2]] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif sound.type == "unknownsound":
                        visited[tk] = "unknown"
                        unknown[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif sound.generated:
                        visited[tk] = "generated"
                        generated[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif str(sound) not in {tk, normalized(tk), normalized(tk, mode='NFC')}:
                        if "/" in tk and str(sound) == tk.split('/')[1]:
                            visited[tk] = "slashed"
                            slashed[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                        else:
                            visited[tk] = "modified"
                            modified[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                else:
                    if visited[tk] == "missing":
                        missing[tk[2:-2]] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "unknown":
                        unknown[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "modified":
                        modified[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "generated":
                        generated[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "slashed":
                        slashed[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]

    print_problems(
        args, generated, 'generated', with_grapheme_uc=True, with_bipa=True,
        add_item=('Non-normal', lambda tk: "*" if tk != str(args.clts.api.bipa[tk]) else ""))
    print_problems(
        args, modified, 'modified', with_grapheme_uc=True, with_bipa=True)
    print_problems(
        args,
        slashed,
        'slashed',
        with_grapheme_uc=lambda tk: codepoints(tk.split('/')[0]),
        with_bipa=True)
    print_problems(args, unknown, 'unknown', add_item=('Diacritics', lambda tk: "◌" + tk))
    print_problems(args, missing, 'missing', add_item=('Diacritics', lambda tk: "◌" + tk))
