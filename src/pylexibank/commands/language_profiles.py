"""
Create a profile for individual languages from an already prepared general profile.
"""
from cldfbench.cli_util import get_dataset
from clldutils.clilib import ParserError
from pycldf import Dataset

from pylexibank.cli_util import add_dataset_spec
from pathlib import Path
from collections import defaultdict
from pylexibank import progressbar
from csvw.dsv import UnicodeDictReader


def register(parser):
    add_dataset_spec(parser)
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Overwrite existing profile',
        default=False)


def run(args):

    ds = get_dataset(args)
    wordlist = Dataset.from_metadata(ds.cldf_dir / "cldf-metadata.json")
    p = ds.etc_dir / "orthography.tsv"
    if not p.exists():
        raise ParserError("profile does not exist but is needed for creation")
    if not ds.etc_dir.joinpath("orthography").exists():
        ds.etc_dir.joinpath("orthography").mkdir(parents=True, exist_ok=True)
    with UnicodeDictReader(p, delimiter="\t") as reader:
        profile = {}
        for row in reader:
            profile[row["Grapheme"]] = row["IPA"]
    
    for language in progressbar(
            wordlist.objects("LanguageTable"), 
            desc="creating profiles"):
        data = defaultdict(int)
        for form in language.forms:
            if form.data.get("Graphemes"):
                for grapheme in form.data["Graphemes"].split():
                    data[grapheme, profile.get(grapheme, "?")] += 1
            else:
                raise ValueError("Grapheme information missing in CLDF data")
        new_path = ds.etc_dir / "orthography" / "{0}.tsv".format(language.id)
        if new_path.exists() and not args.force:
            raise ParserError("Orthography profile exists, use --force to override")
        with open(
                new_path,
                "w",
                encoding="utf-8") as f:
            f.write("{0}\t{1}\t{2}\n".format("Grapheme", "IPA", "Frequency"))
            for (g, s), freq in sorted(
                    data.items(), key=lambda x: x[1],
                    reverse=True):
                f.write("{0}\t{1}\t{2}\n".format(g, s, freq))

