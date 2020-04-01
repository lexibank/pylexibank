"""

"""
import re
import collections

import pyclts
from segments import Tokenizer

from cldfbench.cli_util import add_catalog_spec, get_dataset
from pylexibank.cli_util import add_dataset_spec
from pylexibank.profile import IPA


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, 'clts')

    parser.add_argument(
        "--ipa",
        help="Name of the IPA column (default: `IPA`).",
        default="IPA",
    )
    parser.add_argument(
        '--augment',
        help="augment the profile with frequency counts and examples from the FormTable",
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
    if list(forms.keys()) == [None]:
        forms['default'] = forms[None]

    for key, profile in profiles.items():
        args.log.info('Processing {0}'.format(profile.fname))
        clean_profile(profile, clts, args)

        if args.trim:
            # Run the trimmer as many times as necessary until nothing more is left to remove
            total_removed = 0
            while True:
                removed = profile.trim(ipa_col=args.ipa)
                total_removed += removed
                if removed == 0:
                    break
            if total_removed:
                args.log.info("%i superfluous rules were removed.", total_removed)

        if args.augment and forms[key]:
            profile.augment(forms[key])

        if args.sort:
            profile.sort(clts=args.clts.api, ipa_col=args.ipa)

        check_consistency(profile, clts, args)

        profile.fname.write_text(str(profile), encoding='utf8')


def unicode2codepointstr(text):
    """
    Returns a codepoint representation to an Unicode string.
    """
    return " ".join(["U+{0:0{1}X}".format(ord(char), 4) for char in text])


def check_consistency(profile, clts, args):
    """
    Check a profile for consistency, logging problems.

    For each grapheme, raise:
    - a warning if there are duplicate entries
    - an error if there are inconsistencies
    - an error if the mapping has invalid BIPA
    """
    mapping = collections.defaultdict(list)
    for grapheme, spec in profile.graphemes.items():
        mapping[grapheme].append(spec[args.ipa])

    for grapheme in mapping:
        # check mapping consistency
        if len(mapping[grapheme]) >= 2:
            if len(set(mapping[grapheme])) == 1:
                args.log.warning(
                    "Duplicate (redundant) entry or entries for grapheme [%s].", grapheme)
            else:
                args.log.error(
                    "Inconsist entries for grapheme [%s]: multiple mappings %s.",
                    grapheme,
                    str(mapping[grapheme]),
                )

        # check BIPA consistency
        for value in mapping[grapheme]:
            if value:
                # check for unknown sounds
                unknown = [
                    isinstance(clts.bipa[segment], pyclts.models.UnknownSound)
                    for segment in IPA(value).non_null_tokens]
                if any(unknown):
                    args.log.error(
                        "Mapping [%s] (%s) -> [%s] (%s) includes at least one unknown sound.",
                        grapheme,
                        unicode2codepointstr(grapheme),
                        value,
                        unicode2codepointstr(value),
                    )


def clean_profile(profile, clts, args):
    """
    Replace user-provided IPA graphemes with the CLTS/BIPA default ones.
    """
    def clean_segment(segment, clts):
        if "/" in segment:
            left, right = segment.split("/")
            return "%s/%s" % (left, str(clts.bipa[right]))
        return str(clts.bipa[segment])

    for grapheme, entry in profile.graphemes.items():
        # Remove any multiple spaces, split IPA first into segments and then
        # left- and right- slash information (if any), and use the default
        if entry[args.ipa]:
            ipa_value = re.sub(r"\s+", " ", entry[args.ipa]).strip()
            entry[args.ipa] = " ".join(
                clean_segment(segment, clts) for segment in ipa_value.split())
            if 'CODEPOINTS' in profile.column_labels:
                entry["CODEPOINTS"] = unicode2codepointstr(grapheme)
