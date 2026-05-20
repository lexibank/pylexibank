import pathlib
import collections
import dataclasses
from typing import Optional, Union

import pycldf
from cldfbench.catalogs import Glottolog
import anybadge


@dataclasses.dataclass
class Badge:
    alt: str
    img_url: Union[str, pathlib.Path]
    href: Optional[str] = None

    def as_string(self, dataset):
        img_url = self.img_url
        if isinstance(img_url, pathlib.Path):
            img_url = img_url.relative_to(dataset.dir)
        img = f"![{self.alt}]({img_url})"
        if self.href is None:
            return img
        return f'[{img}]({self.href})'

    @classmethod
    def from_ratio(cls, name: str, ratio: float, fname: pathlib.Path):
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
    def for_github_action(cls, github_repo):
        return cls(
            alt='CLDF validation',
            img_url=f'https://github.com/{github_repo}/workflows/CLDF-validation/badge.svg',
            href=f'https://github.com/{github_repo}/actions?query=workflow%3ACLDF-validation',
        )


def build_status_badge(dataset):
    if dataset.repo and dataset.repo.github_repo:
        if dataset.dir.joinpath('.github/workflows').exists():  # pragma: no cover
            return "[![CLDF validation]" \
                   "(https://github.com/{0}/workflows/CLDF-validation/badge.svg)]" \
                   "(https://github.com/{0}/actions?query=workflow%3ACLDF-validation)" \
                   "".format(dataset.repo.github_repo)
    return ''


def report(dataset, tr_analysis=None, glottolog=None, log=None):
    #
    # FIXME: in case of multiple cldf datasets:
    # - write only summary into README.md
    # - separate lexemes.md and transcriptions.md
    #
    lines = []

    # add NOTES.md
    if dataset.dir.joinpath('NOTES.md').exists():
        lines.append('## Notes\n')
        lines.append(dataset.dir.joinpath('NOTES.md').read_text() + '\n\n')

    badges = []
    if dataset.repo and dataset.repo.github_repo:
        badges.append(Badge.for_github_action(dataset.repo.github_repo))

    for cldf_spec in dataset.cldf_specs_dict.values():
        lines.extend(cldf_report(cldf_spec, tr_analysis, badges, log, glottolog, dataset))
        break
    return '\n'.join(lines)


@dataclasses.dataclass
class Counts:
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
    def SI(self) -> float:
        sindex = sum(
            [sum(list(cnts.values())) / float(len(cnts)) for cnts in self.synonyms.values()])
        langs = set(self.synonyms.keys())
        if langs:
            return sindex / float(len(langs))
        return 0.0  # pragma: no cover

    @property
    def num_cognates(self) -> int:
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
        if self.lexemes == 0:
            return 0.0  # pragma: no cover
        return sum(v for k, v in getattr(self, prop).items() if k) / float(self.lexemes)


def format_ratio(cnt, total):
    return f"{cnt}/{total} ({(cnt / float(total)) * 100:.2f}%%)"


def cldf_report(
        cldf_spec,
        tr_analysis,
        badges,
        log,
        glottolog,
        dataset,
) -> list[str]:
    """Create a report for the dataset."""
    lines = []
    if (not list(cldf_spec.dir.glob('*.csv'))) or (cldf_spec.module != 'Wordlist'):
        return lines

    counts = Counts.from_dataset(cldf_spec.get_dataset(), glottolog)

    stats = tr_analysis['stats'] if tr_analysis else collections.defaultdict(list)
    lsegments = len(stats['segments'])
    lbipapyerr = len(stats['bipa_errors'])
    lsclasserr = len(stats['sclass_errors'])

    badges = badges[:]
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

    lines.extend(['## Statistics', '\n', '\n'.join(b.as_string(dataset) for b in badges), ''])

    stats_lines = [
        '- **Varieties:** {0:,} (linked to {1:,} different Glottocodes)'.format(
            len(counts.lids), sum(1 if gc else 0 for gc in counts.languages)),
        '- **Concepts:** {0:,} (linked to {1:,} different Concepticon concept sets)'.format(
            len(counts.cids), sum(1 if csid else 0 for csid in counts.concepts)),
        '- **Lexemes:** {0:,}'.format(counts.lexemes),
        '- **Sources:** {0:,}'.format(len(counts.sids)),
        '- **Synonymy:** {:0.2f}'.format(counts.SI),
    ]
    if counts.num_cognates:
        stats_lines.extend([
            '- **Cognacy:** {0:,} cognates in {1:,} cognate sets ({2:,} singletons)'.format(
                sum(v for k, v in counts.cognate_sets.items()),
                counts.num_cognates, len([k for k, v in counts.cognate_sets.items() if v == 1])),
            '- **Cognate Diversity:** {:0.2f}'.format(counts.cog_diversity)
        ])
    if stats['segments']:
        stats_lines.extend([
            '- **Invalid lexemes:** {0:,}'.format(stats['invalid_words_count']),
            '- **Tokens:** {0:,}'.format(sum(stats['segments'].values())),
            '- **Segments:** {0:,} ({1} BIPA errors, {2} CLTS sound class errors, '
            '{3} CLTS modified)'
            .format(lsegments, lbipapyerr, lsclasserr, len(stats['replacements'])),
            '- **Inventory size (avg):** {:0.2f}'.format(stats['inventory_size']),
        ])

    if log:
        log.info('\n'.join([f'Summary for dataset {cldf_spec.metadata_path}'] + stats_lines))
    lines.extend(stats_lines)

    # improvements section
    if counts.missing_glottocode or counts.missing_source or counts.bookkeeping_languoids:
        lines.extend(['\n## Possible Improvements:\n', ])

        if counts.missing_glottocode:  # pragma: no cover
            lines.append(
                f"- Languages missing glottocodes: "
                f"{format_ratio(len(counts.missing_glottocode), len(counts.lids))}")

        if counts.bookkeeping_languoids:  # pragma: no cover
            lines.append(
                "- Languages linked to [bookkeeping languoids in Glottolog]"
                "(https://glottolog.org/glottolog/glottologinformation"
                "#bookkeepinglanguoids):")
        for lang in counts.bookkeeping_languoids:  # pragma: no cover
            lines.append(
                f"  - {lang.get('Name', lang.get('ID'))} [{lang['Glottocode']}]"
                f"(https://glottolog.org/resource/languoid/id/{lang['Glottocode']})")

        if counts.missing_source:
            lines.append(
                f"- Entries missing sources: "
                f"{format_ratio(len(counts.missing_source), counts.lexemes)}")
        lines.append('\n')

    return lines
