"""
Format (and lint) the orthography profiles of a dataset.
"""
import collections

from cldfbench.cli_util import add_catalog_spec, get_dataset
from pylexibank.cli_util import add_dataset_spec
from pylexibank.profile import IPA_COLUMN


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, 'clts')

    parser.add_argument(
        "--ipa",
        help="Name of the profile column with the IPA representation.",
        default=IPA_COLUMN,
    )
    parser.add_argument(
        '--augment',
        help="augment the profile with sca, and frequency counts and examples from the FormTable",
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '--trim',
        help="remove redundant orthography rules",
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '--sort',
        help="sort the profile",
        default=False,
        action='store_true',
    )


def run(args):
    ds = get_dataset(args)
    clts = args.clts.api

    # Load the profile(s) specified for the dataset
    profiles = {k or 'default': v for k, v in ds.orthography_profile_dict.items()}
    forms = collections.defaultdict(list)
    if ds.cldf_dir.joinpath('forms.csv').exists():
        for form in ds.cldf_reader()['FormTable']:
            forms[form.get('Profile')].append(ds.form_for_segmentation(form['Form']))
    if list(forms.keys()) == [None]:  # pragma: no cover
        forms['default'] = forms[None]

    for key, profile in profiles.items():
        args.log.info('Processing {0}'.format(profile.fname))
        profile.clean(clts, ipa_col=args.ipa)

        if args.trim:
            # Run the trimmer as many times as necessary until nothing more is left to remove
            total_removed = 0
            while True:
                removed = profile.trim(ipa_col=args.ipa)
                total_removed += removed
                if removed == 0:
                    break
            if total_removed:  # pragma: no cover
                args.log.info("{} superfluous rules were removed.".format(total_removed))

        if args.augment and forms[key]:
            profile.augment(forms[key], clts=args.clts.api)

        if args.sort:
            profile.sort(clts=args.clts.api, ipa_col=args.ipa)

        profile.check(clts, args.log, ipa_col=args.ipa)
        profile.write()
