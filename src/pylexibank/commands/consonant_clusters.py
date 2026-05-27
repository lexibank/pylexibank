"""
Check for (potentially) problematic consonant clusters >= 3.
"""
import operator
import itertools
import collections

from cldfbench.cli_util import with_dataset, add_catalog_spec
from clldutils.clilib import Table, add_format

from pylexibank.cli_util import add_dataset_spec
from pylexibank.forms import compute_consonant_cluster


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser)
    add_catalog_spec(parser, "clts")
    add_format(parser, default="pipe")

    parser.add_argument(
        "-l", "--length",
        type=int,
        default=3,
        help="Check for consonant clusters of this length or more"
    )


def run(args):  # pylint: disable=C0116
    with_dataset(args, analyze_consonant_clusters)


def analyze_consonant_clusters(dataset, args):
    """Analyzes clusters of consonants found in the segmented forms of the dataset."""
    by_lang: dict[tuple, dict[str, list[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for row in sorted(
            dataset.cldf_dir.read_csv("forms.csv", dicts=True), key=operator.itemgetter('ID')
    ):
        if "<<" in row["Segments"]:
            args.log.warning("Invalid segments in %s (ID: %s).", row["Segments"], row["ID"])
            continue

        for morpheme in row["Segments"].split(" + "):
            for cluster in compute_consonant_cluster(morpheme.split(), args.clts.api):
                by_lang[tuple(cluster)][row["Language_ID"]] += [row["Form"]]

    with Table(args, "Language_ID", "Length", "Cluster", "Words") as table:
        cases = 0
        for cluster in itertools.takewhile(
            lambda c: len(c) >= args.length, sorted(by_lang, key=len, reverse=True)
        ):
            cases += 1
            for language, words in by_lang[cluster].items():
                table.append([language, str(len(cluster)), " ".join(cluster), " // ".join(words)])

    args.log.warning(
        f"{cases} potentially problematic consonant cluster(s) with length >= {args.length}.")
