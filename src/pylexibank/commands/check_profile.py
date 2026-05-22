"""
Check forms against a dataset's orthography profile.
"""
from cldfbench.cli_util import with_dataset, add_catalog_spec
from clldutils.clilib import Table, add_format

from pylexibank.cli_util import add_dataset_spec, read_forms
from pylexibank.profile import Checker, normalized, unicode2codepointstr, SegmentProblem


def register(parser):  # pylint: disable=C0116
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


def run(args):  # pylint: disable=C0116
    with_dataset(args, check_profile)


def check_profile(dataset, args):
    """
    Checks the orthography profile(s) of a dataset by using it to tokenize the forms and inspecting
    the results.
    """
    checker = Checker(args.clts.api)

    for row in read_forms(dataset):
        if not args.language or args.language == row["languageReference"]:
            kw = {'column': "IPA"}
            if 'Profile' in row:  # A multi-profile dataset.
                kw['profile'] = None if row['Profile'] == 'default' else row['Profile']
            tokens = [normalized(t) for t in (
                dataset.tokenizer(row, row["form"], **kw)
                if dataset.tokenizer and not args.noprofile
                else row["segments"]
            )]
            checker(tokens, row['form'], row['Graphemes'])

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
        for cat, tokens in checker.problems.items():
            for tk, segmented_forms in tokens.items():
                table.append([
                    cat.name,
                    tk,
                    unicode2codepointstr(tk.split('/')[0] if cat == SegmentProblem.slashed else tk),
                    "*" if cat == SegmentProblem.generated and tk != str(args.clts.api.bipa[tk])
                    else "",
                    "◌" + tk if cat in {SegmentProblem.missing, SegmentProblem.unknown} else '',
                    str(args.clts.api.bipa[tk]),
                    args.clts.api.bipa[tk].codepoints,
                    segmented_forms[0].segments,
                    segmented_forms[0].graphemes,
                    len(segmented_forms),
                ])
