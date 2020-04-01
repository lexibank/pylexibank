import re
import copy
import collections

import segments
from segments.tree import Tree


class IPA:
    def __init__(self, text):
        self.text = text
        self.tokens = [t if "/" not in t else t.split("/")[1] for t in (text or '').split()]
        self.non_null_tokens = [t for t in self.tokens if t and t != "NULL"]

    def types(self, clts):
        return " ".join(
            type(clts.bipa[token]).__name__ if token != "NULL" else "NULL" for token in self.tokens)

    def sca(self, clts):
        sca = clts.soundclass("sca")
        return " ".join(
            clts.bipa.translate(token, sca) if token != "NULL" else "NULL" for token in self.tokens)


class Profile(segments.Profile):
    def __init__(self, *specs, **kw):
        super().__init__(*specs, **kw)
        default_spec = list(next(iter(self.graphemes.values())).keys())
        for grapheme in ['^', '$']:
            if grapheme not in self.graphemes:
                self.graphemes[grapheme] = {k: None for k in default_spec}
        self.recreate_tree()

    def recreate_tree(self):
        self.tree = Tree(list(self.graphemes.keys()))

    def sort(self, clts=None, ipa_col='IPA'):
        self.graphemes = collections.OrderedDict(
            sorted(
                self.graphemes.items(),
                key=lambda e: (
                    e[0] not in ["^", "$"],
                    e[0] != "^",
                    e[1][ipa_col] != None,
                    re.match("\^.*\$", e[0]) is None,
                    len(IPA(e[1][ipa_col]).sca(clts)) if clts else False,
                    IPA(e[1][ipa_col]).sca(clts) if clts else False,
                    len(e[0]),
                    e[0],
                ),
            )
        )

    def trim(self, ipa_col='IPA'):
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
            if grapheme not in new_profile:
                continue
            ipa = new_profile[grapheme][ipa_col]
            # Obtain the segments without the current rule
            t = segments.Tokenizer(
                profile=Profile(*[copy.copy(s) for g, s in new_profile.items() if g != grapheme]))
            if t(grapheme, column=ipa_col) == ipa:
                # If the resulting `segments` match the `ipa` reference, don't add the
                # rule back (but keep track of how many were removed)
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

    def augment(self, forms):
        """
        Applies a profile to a wordlist, returning new profile counts and segments.
        """
        self.column_labels.add('FREQUENCY')
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
