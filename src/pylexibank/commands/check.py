from collections import Counter

import pytest
from clldutils.clilib import command  # , confirm, ParserError
from pylexibank.commands.util import get_dataset
from termcolor import colored


@command()
def check(args):
    ds = get_dataset(args)

    # validate
    print(colored("Validating CLDF...", "green"))
    ds.cldf.validate()

    # tests
    testfile = ds.dir / "test.py"
    if testfile.is_file():
        print(colored("Running tests...", "green"))
        pytest.main([
            '--cldf-metadata=%s/cldf-metadata.json' % ds.cldf_dir,
            testfile
        ])
    else:
        print(colored("No tests found", "red"))

    # Check languages
    print(colored("Checking Languages...", "green"))
    for lang in ds.cldf['LanguageTable']:
        if not lang['Glottocode']:
            print(colored(
                "Warning: Language '%s' is missing a glottocode" % lang['Name'],
                "yellow"
            ))
        else:
            found = ds.glottolog.languoid(lang['Glottocode'])
            if not found:
                print(colored(
                    "ERROR: Language '%s' has an INVALID glottocode '%s'" % (
                    lang['Name'], lang['Glottocode']),
                    "red"
                ))
    
    # Check sources
    print(colored("Checking Sources...", "green"))
    sources_in_forms = check_sources(ds.cldf)
    sources_in_bib = ds.cldf.wl.sources.keys()
    for s in sources_in_forms:
        if s not in sources_in_bib:
            print("Warning: Source '%s' is not defined in sources.bib" % s)
        if s == "":
            print(
                "Warning: %d lexemes have no source defined" % sources_in_forms[s]
            )


def check_sources(cldf):
    sources = Counter(s for row in cldf['FormTable'] for s in row['Source'])
    return sources
