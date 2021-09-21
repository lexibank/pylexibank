"""
Check forms against a dataset's orthography profile.
"""
from cldfbench.cli_util import with_dataset, add_catalog_spec
from clldutils.clilib import Table, add_format
from pylexibank.cli_util import add_dataset_spec
from unicodedata import normalize


def normalized(string):
    return normalize("NFD", string)


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
        action="store_true")


def codepoints(string):
    out = []
    for char in string:
        out += [hex(ord(char))[2:]]
    return " ".join(["U+" + x.rjust(4, "0") for x in out])


def run(args):
    with_dataset(args, check_profile)


def check_profile(dataset, args):
    visited = {}
    missing, unknown, modified, generated, slashed = {}, {}, {}, {}, {}
    for row in dataset.cldf_dir.read_csv("forms.csv", dicts=True):
        if not args.language or args.language == row["Language_ID"]:
            tokens = [normalized(t) for t in (
                dataset.tokenizer(row, row["Form"], column="IPA")
                if dataset.tokenizer and not args.noprofile
                else row["Segments"].split()
            )]
            for tk in set(tokens):
                if tk not in visited:
                    sound = args.clts.api.bipa[tk]
                    if tk.startswith("<<") and tk.endswith(">>"):
                        visited[tk] = "missing"
                        missing[tk[2:-2]] = [
                            (" ".join(tokens), row["Form"], row["Graphemes"])
                        ]
                    elif sound.type == "unknownsound":
                        visited[tk] = "unknown"
                        unknown[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif sound.generated:
                        visited[tk] = "generated"
                        generated[tk] = [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif str(sound) != tk and str(sound) != normalized(tk):
                        if "/" in tk and str(sound) == tk.split('/')[1]:
                            visited[tk] = "slashed"
                            slashed[tk] = [
                                (" ".join(tokens), row["Form"], row["Graphemes"])]
                        else:
                            visited[tk] = "modified"
                            modified[tk] = [
                                (" ".join(tokens), row["Form"], row["Graphemes"])]
                else:
                    if visited[tk] == "missing":
                        missing[tk[2:-2]] += [
                            (" ".join(tokens), row["Form"], row["Graphemes"])
                        ]
                    elif visited[tk] == "unknown":
                        unknown[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "modified":
                        modified[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]
                    elif visited[tk] == "generated":
                        generated[tk] += [(" ".join(tokens), row["Form"], row["Graphemes"])]

    if generated:
        print("# Found {0} generated graphemes".format(len(generated)))
        with Table(
            args, *["Grapheme", "Grapheme-UC", "BIPA", "BIPA-UC", "Modified",
                    "Segments", "Graphemes", "Count"]
        ) as table:
            for tk, values in sorted(generated.items(), key=lambda x: len(x[1])):
                table.append(
                    [
                        tk,
                        codepoints(tk),
                        str(args.clts.api.bipa[tk]),
                        args.clts.api.bipa[tk].codepoints,
                        "*" if tk != str(args.clts.api.bipa[tk]) else "",
                        values[0][0],
                        values[0][1],
                        len(values),
                    ]
                )
    if modified:
        print("# Found {0} modified graphemes".format(len(modified)))
        with Table(
            args, *["Grapheme", "Grapheme-UC", "BIPA", "BIPA-UC", "Segments", "Graphemes", "Count"]
        ) as table:
            for tk, values in sorted(modified.items(), key=lambda x: len(x[1])):
                table.append(
                    [
                        tk,
                        codepoints(tk),
                        str(args.clts.api.bipa[tk]),
                        args.clts.api.bipa[tk].codepoints,
                        values[0][0],
                        values[0][1],
                        len(values),
                    ]
                )
    if slashed:
        print("# Found {0} slashed graphemes".format(len(slashed)))
        with Table(
            args, *["Grapheme", "Grapheme-UC", "BIPA", "BIPA-UC", "Segments", "Graphemes", "Count"]
        ) as table:
            for tk, values in sorted(slashed.items(), key=lambda x: len(x[1])):
                table.append(
                    [
                        tk,
                        codepoints(tk.split('/')[0]),
                        str(args.clts.api.bipa[tk]),
                        args.clts.api.bipa[tk].codepoints,
                        values[0][0],
                        values[0][1],
                        len(values),
                    ]
                )

    if unknown:
        print("# Found {0} unknown graphemes".format(len(unknown)))
        with Table(
            args,
            *["Grapheme", "Diacritics", "Unicode", "Segments", "Graphemes", "Count"]
        ) as table:
            for tk, values in sorted(unknown.items(), key=lambda x: len(x[1])):
                table.append(
                    [
                        tk,
                        "◌" + tk,
                        args.clts.api.bipa[tk].codepoints,
                        values[0][0],
                        values[0][1],
                        len(values),
                    ]
                )
    if missing:
        print("# Found {0} graphemes missing in profile".format(len(missing)))
        with Table(
            args,
            *["Grapheme", "Diacritics", "Unicode", "Segments", "Graphemes", "Count"]
        ) as table:
            for tk, values in sorted(missing.items(), key=lambda x: len(x[1])):
                table.append(
                    [
                        tk,
                        "◌" + tk,
                        args.clts.api.bipa[tk].codepoints,
                        values[0][0],
                        values[0][1],
                        len(values),
                    ]
                )
