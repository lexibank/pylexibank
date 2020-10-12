"""
Orthography profiles in lexibank are based on the Profile class in the `segments` package, adding
functionality to check and consistently format in a diff-friendly way.
"""
import re
import copy
import collections

import pyclts
import segments
from segments.tree import Tree
from clldutils.misc import log_or_raise
from csvw import dsv
from csvw.metadata import TableGroup, Column

__all__ = ['Profile', 'IPA_COLUMN']

IPA_COLUMN = 'IPA'


def unicode2codepointstr(text):
    return " ".join(["U+{0:0{1}X}".format(ord(char), 4) for char in text])


def ipa2tokens(text):
    return [t if "/" not in t else t.split("/")[1] for t in (text or '').split()]


def ipa2sca(text, clts):
    sca = clts.soundclass("sca")
    return " ".join(
        clts.bipa.translate(t, sca) if t != "NULL" else "NULL" for t in ipa2tokens(text))


class Profile(segments.Profile):
    def __init__(self, *specs, **kw):
        super().__init__(*specs, **kw)
        default_spec = list(next(iter(self.graphemes.values())).keys())
        for grapheme in ['^', '$']:
            if grapheme not in self.graphemes:
                self.graphemes[grapheme] = {k: None for k in default_spec}
        self.recreate_tree()

    def __str__(self):
        # We overwrite the base class' method to fix the order of columns.
        tg = TableGroup.fromvalue(self.MD)
        for col in sorted(
                self.column_labels, key=lambda t: (t == IPA_COLUMN, t.lower()), reverse=True):
            if col != self.GRAPHEME_COL:
                tg.tables[0].tableSchema.columns.append(
                    Column.fromvalue({"name": col, "null": self.NULL}))

        return tg.tables[0].write(self.iteritems(), fname=None).decode('utf8').strip()

    def write(self, fname=None):
        (fname or self.fname).write_text(str(self), encoding='utf8')

    def recreate_tree(self):
        self.tree = Tree(list(self.graphemes.keys()))

    def sort(self, clts=None, ipa_col=IPA_COLUMN):
        self.graphemes = collections.OrderedDict(
            sorted(
                self.graphemes.items(),
                key=lambda e: (
                    e[0] not in ["^", "$"],
                    e[0] != "^",
                    e[1][ipa_col] != None,
                    re.match(r"\^.*\$", e[0]) is None,
                    len(ipa2sca(e[1][ipa_col], clts)) if clts else False,
                    ipa2sca(e[1][ipa_col], clts) if clts else False,
                    len(e[0]),
                    e[0],
                ),
            )
        )

    def trim(self, ipa_col=IPA_COLUMN):
        # Make a copy of the profile (so we don't change in place)
        new_profile = collections.OrderedDict()
        for g, entry in self.graphemes.items():
            spec = copy.copy(entry)
            spec[self.GRAPHEME_COL] = g
            new_profile[g] = spec

        # Collect all keys, so that we will gradually remove them; those with
        # ^ and $ go first
        graphemes = list(new_profile.keys())
        bound_graphemes = [
            grapheme for grapheme in graphemes if grapheme[0] == "^" and grapheme[-1] == "$"]
        bound_graphemes += [
            grapheme for grapheme in graphemes if grapheme[0] == "^" and grapheme[-1] != "$"]
        bound_graphemes += [
            grapheme for grapheme in graphemes if grapheme[0] != "^" and grapheme[-1] == "$"]

        check_graphemes = bound_graphemes + sorted(
            [
                grapheme
                for grapheme in graphemes if len(grapheme) > 1 and grapheme not in bound_graphemes
            ],
            key=len,
            reverse=True,
        )

        # For each entry, we will remove it from `segment_map`, apply the resulting
        # profile, and add the entry back at the end of loop (still expansive, but
        # orders of magnitude less expansive than making a copy at each iteration)
        removed = 0
        for grapheme in check_graphemes:
            if grapheme in new_profile:
                ipa = new_profile[grapheme][ipa_col]
                # Obtain the segments without the current rule
                t = segments.Tokenizer(
                    profile=Profile(
                        *[copy.copy(s) for g, s in new_profile.items() if g != grapheme]))
                if t(grapheme, column=ipa_col) == ipa:
                    # If the resulting `segments` match the `ipa` reference, we can delete the rule:
                    removed += 1
                    del new_profile[grapheme]

        for g in set(self.graphemes.keys()) - set(new_profile.keys()):
            del self.graphemes[g]

        self.recreate_tree()
        return removed

    @staticmethod
    def segmentable_form(form):
        form = form.strip()
        if not form.startswith('^'):
            form = '^' + form
        if not form.endswith('$'):
            form += '$'
        return form

    def augment(self, forms, clts=None, ipa_col=IPA_COLUMN):
        """
        Applies a profile to a wordlist, returning new profile counts and segments.
        """
        self.column_labels.add('FREQUENCY')
        if clts:
            self.column_labels.add('SCA')
        self.column_labels.add('EXAMPLES')
        freqs = collections.Counter()
        ex = collections.defaultdict(list)
        t = segments.Tokenizer(profile=self)
        for form in forms:
            graphemes = t(self.segmentable_form(form)).split()
            freqs.update(graphemes)
            for g in graphemes:
                ex[g].append(form[1:-1])
        for g, spec in self.graphemes.items():
            spec['FREQUENCY'] = freqs.get(g, 0)
            spec['EXAMPLES'] = ";".join(ex.get(g, [])[:5])
            if clts:
                spec['SCA'] = ipa2sca(spec[ipa_col], clts)

    def clean(self, clts, ipa_col=IPA_COLUMN):
        """
        Replace user-provided IPA graphemes with the CLTS/BIPA default ones.
        """
        def clean_segment(segment, clts):
            if "/" in segment:
                left, right = segment.split("/")
                return "%s/%s" % (left, str(clts.bipa[right]))
            return str(clts.bipa[segment])

        for grapheme, entry in self.graphemes.items():
            # Remove any multiple spaces, split IPA first into segments and then
            # left- and right- slash information (if any), and use the default
            if entry[ipa_col]:
                ipa_value = re.sub(r"\s+", " ", entry[ipa_col]).strip()
                entry[ipa_col] = " ".join(
                    clean_segment(segment, clts) for segment in ipa_value.split())
                if 'CODEPOINTS' in self.column_labels:
                    entry["CODEPOINTS"] = unicode2codepointstr(grapheme)

    def check(self, clts=None, log=None, ipa_col=IPA_COLUMN):
        """
        Check a profile for consistency, logging problems.

        For each grapheme, raise:
        - a warning if there are duplicate entries
        - an error if there are inconsistencies
        - an error if the mapping has invalid BIPA
        """
        mapping = collections.defaultdict(list)
        if self.fname:
            # We read the profile from disk because segments.Profile already skips duplicate
            # graphemes, which we want to investigate more closely.
            for spec in dsv.reader(self.fname, dicts=True, delimiter='\t'):
                mapping[spec[self.GRAPHEME_COL]].append(spec[ipa_col])

        for grapheme in mapping:
            # check mapping consistency
            if len(mapping[grapheme]) >= 2:
                if len(set(mapping[grapheme])) == 1:
                    log_or_raise(
                        "Duplicate, redundant entry or entries for grapheme [{}].".format(grapheme),
                        log=log,
                        level='warning')
                else:
                    log_or_raise(
                        "Inconsist entries for grapheme [{}]: multiple mappings {}.".format(
                            grapheme,
                            str(mapping[grapheme])),
                        log=log,
                        level='error')

            # check BIPA consistency
            if clts:
                for value in mapping[grapheme]:
                    if value:
                        # check for unknown sounds
                        unknown = [
                            isinstance(clts.bipa[segment], pyclts.models.UnknownSound)
                            for segment in ipa2tokens(value) if segment and segment != 'NULL']
                        if any(unknown):
                            log_or_raise(
                                "Mapping [{}] ({}) -> [{}] ({}) includes an unknown sound.".format(
                                    grapheme,
                                    unicode2codepointstr(grapheme),
                                    value,
                                    unicode2codepointstr(value)),
                                log=log,
                                level='error'
                            )
