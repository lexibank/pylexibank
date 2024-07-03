"""
Check for (potentially) problematic consonant clusters >= 3.
"""

import collections

from cldfbench.cli_util import with_dataset, add_catalog_spec
from clldutils.clilib import Table, add_format

from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, "clts")
    add_format(parser, default="pipe")

    parser.add_argument(
        "-l", "--length",
        type=int,
        default=3,
        help="Check for consonant clusters of this length or more"
    )


def run(args):
    with_dataset(args, collect_consonant_clusters)


def compute_consonant_cluster(word, sound_names):
    out = [[]] if sound_names[0].split(" ")[-1] in ["consonant", "cluster"] else []
    for i, sound in enumerate(sound_names):
        if sound.split(" ")[-1] in ["diphthong", "vowel", "tone", "�", "marker"]:
            out += [[]]
        else:
            out[-1] += [word[i]]
    return [chunk for chunk in out if chunk]


def collect_consonant_clusters(dataset, args):
    by_lang = collections.defaultdict(lambda: collections.defaultdict(list))

    with Table(args, "Language_ID", "Length", "Cluster", "Words") as table:
        for row in sorted(
            dataset.cldf_dir.read_csv("forms.csv", dicts=True), key=lambda r: r["ID"]
        ):
            if "<<" in row["Segments"]:
                args.log.warning(
                    "Invalid segments in {0} (ID: {1}).".format(row["Segments"], row["ID"]))
                continue
            else:
                segments = row["Segments"].split(" + ")

            for morpheme, sounds in map(
                lambda x: (x.split(), [s.name for s in args.clts.api.bipa(x.split())]),
                segments
            ):
                clusters = compute_consonant_cluster(morpheme, sounds)

                for cluster in clusters:
                    by_lang[tuple(cluster)][row["Language_ID"]] += [row["Segments"], row["Form"]]

        cases = 0
        for cluster in sorted(by_lang, key=lambda x: len(x)):
            data = by_lang[cluster]
            if len(cluster) >= args.length:
                cases += 1
                for language, words in data.items():
                    table.append(
                        [language, str(len(cluster)), " ".join(cluster), " // ".join(words)])

    args.log.warning(
        f"Found {cases} potentially problematic consonant cluster(s) with length {args.length}.")
