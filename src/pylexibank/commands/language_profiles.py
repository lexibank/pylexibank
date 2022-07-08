"""
Create a profile for individual languages from an already prepared general profile.
"""
from collections import defaultdict

from cldfbench.cli_util import get_dataset
from clldutils.clilib import ParserError
from pycldf import Dataset
from csvw.dsv import reader, UnicodeWriter

from pylexibank import progressbar
from pylexibank.cli_util import add_dataset_spec


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
    profile = {row["Grapheme"]: row["IPA"] for row in reader(p, delimiter='\t')}

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
        with UnicodeWriter(new_path, delimiter='\t') as writer:
            writer.writerow(["Grapheme", "IPA", "Frequency"])
            for (g, s), freq in sorted(data.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([g, s, freq])
