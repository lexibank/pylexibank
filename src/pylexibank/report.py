"""
Functionality to create a human readable report on a dataset.
"""
import pathlib
import collections
from collections.abc import Generator
import dataclasses
from typing import Optional, Union

import pycldf
from cldfbench.catalogs import Glottolog
import anybadge


@dataclasses.dataclass
class Badge:
    """A badge."""
    alt: str
    img_url: Union[str, pathlib.Path]
    href: Optional[str] = None

    def as_string(self, dataset) -> str:
        """Serialize the badge as markdown image link."""
        img_url = self.img_url
        if isinstance(img_url, pathlib.Path):
            img_url = img_url.relative_to(dataset.dir)
        img = f"![{self.alt}]({img_url})"
        if self.href is None:
            return img
        return f'[{img}]({self.href})'

    @classmethod
    def from_ratio(cls, name: str, ratio: float, fname: pathlib.Path):
        """Create a badge displaying some generic ratio."""
        thresholds = {
            60: 'red',
            70: 'orange',
            80: 'yellow',
            90: 'yellowgreen',
            99: 'greenyellow',
            101: 'green',
        }
        fname.parent.mkdir(exist_ok=True)
        if fname.exists():
            fname.unlink()
        anybadge.Badge(
            label=name,
            value=int(round(ratio * 100)),
            value_suffix='%',
            thresholds=thresholds,
        ).write_badge(fname)
        return cls(alt=f'{name}: {int(round(ratio * 100))}%', img_url=fname)

    @classmethod
    def for_github_action(cls, github_repo) -> 'Badge':
        """Create a GitHub actions badge for the CLDF validation task."""
        return cls(
            alt='CLDF validation',
            img_url=f'https://github.com/{github_repo}/workflows/CLDF-validation/badge.svg',
            href=f'https://github.com/{github_repo}/actions?query=workflow%3ACLDF-validation',
        )


def report(dataset, tr_analysis=None, glottolog=None, log=None) -> str:
    """Create a markdown-formatted report for a dataset."""
    #
    # FIXME: in case of multiple cldf datasets:  # pylint: disable=fixme
    # - write only summary into README.md
    # - separate lexemes.md and transcriptions.md
    #
    lines = []

    # add NOTES.md
    if dataset.dir.joinpath('NOTES.md').exists():
        lines.append('## Notes\n')
        lines.append(dataset.dir.joinpath('NOTES.md').read_text() + '\n\n')

    for cldf_spec in dataset.cldf_specs_dict.values():
        if list(cldf_spec.dir.glob('*.csv')) and cldf_spec.module == 'Wordlist':
            lines.extend(
                iter_cldf_report_lines(cldf_spec, tr_analysis, log, glottolog, dataset))
            break
    return '\n'.join(lines)


@dataclasses.dataclass
class Counts:  # pylint: disable=R0902
    """
    Counts of stuff in a dataset to compute summary statistics from.
    """
    languages: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    concepts: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    sources: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    cognate_sets: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    lexemes: int = 0
    lids: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    cids: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    sids: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    synonyms: dict[str, collections.Counter] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(collections.Counter))
    missing_source: list[dict] = dataclasses.field(default_factory=list)
    missing_glottocode: list[dict] = dataclasses.field(default_factory=list)
    bookkeeping_languoids: list[dict] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dataset(cls, cldf: pycldf.Dataset, glottolog: Optional[Glottolog]):
        """Update with the data of a row in FormTable"""
        param2concepticon = {r['ID']: r['Concepticon_ID'] for r in cldf['ParameterTable']}
        lang2glottolog = {r['ID']: r['Glottocode'] for r in cldf['LanguageTable']}

        cnt = cls()

        for row in cldf['FormTable']:
            if row['Source']:
                cnt.sources.update(['y'])
                cnt.sids.update(row['Source'])
            else:
                cnt.missing_source.append(row)
            cnt.concepts.update([param2concepticon[row['Parameter_ID']]])
            cnt.languages.update([lang2glottolog[row['Language_ID']]])
            cnt.lexemes += 1
            cnt.lids.update([row['Language_ID']])
            cnt.cids.update([row['Parameter_ID']])
            cnt.synonyms[row['Language_ID']].update([row['Parameter_ID']])

        for row in cldf.get('CognateTable') or []:
            cnt.cognate_sets.update([row['Cognateset_ID']])

        bookkeeping_languoids_in_gl = set()
        if glottolog:
            for lang in glottolog.api.languoids():
                if lang.category == 'Bookkeeping':
                    bookkeeping_languoids_in_gl.add(lang.id)  # pragma: no cover
        for lang in cldf.iter_rows('LanguageTable', 'glottocode'):
            if lang.get('glottocode'):
                if lang['glottocode'] in bookkeeping_languoids_in_gl:
                    cnt.bookkeeping_languoids.append(lang)  # pragma: no cover
            else:
                cnt.missing_glottocode.append(lang)
        return cnt

    @property
    def synonymy_index(self) -> float:
        """A measure for the amount of synonyms in a dataset."""
        sindex = sum(sum(cnts.values()) / float(len(cnts)) for cnts in self.synonyms.values())
        langs = set(self.synonyms.keys())
        if langs:
            return sindex / float(len(langs))
        return 0.0  # pragma: no cover

    @property
    def num_cognates(self) -> int:
        """The number of cognate sets."""
        return len(self.cognate_sets)

    @property
    def cog_diversity(self) -> float:
        """
        see List et al. 2017
        diff between cognate sets and meanings / diff between words and meanings
        """
        try:
            return (self.num_cognates - len(self.cids)) / (self.lexemes - len(self.cids))
        except ZeroDivisionError:
            return 0.0  # no lexemes.

    def ratio(self, prop: str) -> float:
        """Ratio for a given property, relative to the number of lexemes."""
        if self.lexemes == 0:
            return 0.0  # pragma: no cover
        return sum(v for k, v in getattr(self, prop).items() if k) / float(self.lexemes)

    @property
    def distinct_glottocodes(self):
        """The number of distinct glottocodes linked to in a dataset."""
        return sum(1 if gc else 0 for gc in self.languages)

    @property
    def distinct_conceptsets(self) -> int:
        """The number of distinct conceptsets linked to in a dataset."""
        return sum(1 if cs else 0 for cs in self.concepts)


def format_ratio(cnt: int, total: int) -> str:
    """Format a ration as fraction and as percentage."""
    return f"{cnt}/{total} ({(cnt / float(total)) * 100:.2f}%%)"


def iter_cldf_report_lines(
        cldf_spec,
        tr_analysis,
        log,
        glottolog,
        dataset,
) -> Generator[str, None, None]:
    """Create a report for the dataset."""
    counts = Counts.from_dataset(cldf_spec.get_dataset(), glottolog)

    stats = tr_analysis['stats'] if tr_analysis else collections.defaultdict(list)
    lsegments = len(stats['segments'])
    lbipapyerr = len(stats['bipa_errors'])
    lsclasserr = len(stats['sclass_errors'])

    badges = []
    if dataset.repo and dataset.repo.github_repo:
        badges.append(Badge.for_github_action(dataset.repo.github_repo))

    for name, prop in [
            ('Glottolog', 'languages'), ('Concepticon', 'concepts'), ('Source', 'sources')]:
        badges.append(
            Badge.from_ratio(name, counts.ratio(prop), dataset.etc_dir / f'badge_{prop}.svg'))
    if lsegments:
        badges.extend([
            Badge.from_ratio(
                'BIPA', (lsegments - lbipapyerr) / lsegments, dataset.etc_dir / 'badge_bipa.svg'),
            Badge.from_ratio(
                'CLTS SoundClass',
                (lsegments - lsclasserr) / lsegments,
                dataset.etc_dir / 'badge_sc.svg'),
        ])

    yield from ['## Statistics', '\n', '\n'.join(b.as_string(dataset) for b in badges), '']

    stats_lines = [
        f'- **Varieties:** {len(counts.lids):,} (linked to '
        f'{counts.distinct_glottocodes:,} different Glottocodes)',
        f'- **Concepts:** {len(counts.cids):,} (linked to '
        f'{counts.distinct_conceptsets:,} different Concepticon concept sets)',
        f'- **Lexemes:** {counts.lexemes:,}',
        f'- **Sources:** {len(counts.sids):,}',
        f'- **Synonymy:** {counts.synonymy_index:0.2f}',
    ]
    if counts.num_cognates:
        stats_lines.extend([
            f'- **Cognacy:** {sum(v for k, v in counts.cognate_sets.items()):,} '
            f'cognates in {counts.num_cognates:,} cognate sets '
            f'({len([k for k, v in counts.cognate_sets.items() if v == 1]):,} singletons)',
            f'- **Cognate Diversity:** {counts.cog_diversity:0.2f}'
        ])
    if stats['segments']:
        stats_lines.extend([
            f'- **Invalid lexemes:** {stats["invalid_words_count"]:,}',
            f'- **Tokens:** {sum(stats["segments"].values()):,}',
            f'- **Segments:** {lsegments:,} ({lbipapyerr} BIPA errors, '
            f'{lsclasserr} CLTS sound class errors, {len(stats["replacements"])} CLTS modified)',
            f'- **Inventory size (avg):** {stats["inventory_size"]:0.2f}',
        ])

    if log:
        log.info('\n'.join([f'Summary for dataset {cldf_spec.metadata_path}'] + stats_lines))
    yield from stats_lines

    # improvements section
    if counts.missing_glottocode or counts.missing_source or counts.bookkeeping_languoids:
        yield '\n## Possible Improvements:\n'

        if counts.missing_glottocode:  # pragma: no cover
            yield (f"- Languages missing glottocodes: "
                   f"{format_ratio(len(counts.missing_glottocode), len(counts.lids))}")

        if counts.bookkeeping_languoids:  # pragma: no cover
            yield ("- Languages linked to [bookkeeping languoids in Glottolog]"
                   "(https://glottolog.org/glottolog/glottologinformation#bookkeepinglanguoids):")
        for lang in counts.bookkeeping_languoids:  # pragma: no cover
            yield (f"  - {lang.get('Name', lang.get('ID'))} [{lang['Glottocode']}]"
                   f"(https://glottolog.org/resource/languoid/id/{lang['Glottocode']})")

        if counts.missing_source:
            yield (f"- Entries missing sources: "
                   f"{format_ratio(len(counts.missing_source), counts.lexemes)}")
        yield ''
