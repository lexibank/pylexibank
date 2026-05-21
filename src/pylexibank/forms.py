"""
Form handling.
"""
import re
import logging
import dataclasses
import unicodedata
from typing import Literal, Optional
from collections.abc import Iterable

from clldutils import text
from clldutils import misc

__all__ = ['FormSpec']
log = logging.getLogger('pylexibank')


def dcfield(help_, **kw):
    """A dataclasses field with help."""
    kw['metadata'] = {"help": help_}
    return dataclasses.field(**kw)  # pylint: disable=E3701


@dataclasses.dataclass
class FormSpec:  # pylint: disable=R0902
    """
    Specification of the value-to-form processing in Lexibank datasets:

    The value-to-form processing is divided into two steps, implemented as methods:
    - `FormSpec.split`: Splits a string into individual form chunks.
    - `FormSpec.clean`: Normalizes a form chunk.

    These methods use the attributes of a `FormSpec` instance to configure their behaviour.
    """
    brackets: dict = dcfield(
        "Pairs of strings that should be recognized as brackets, specified as `dict` "
        "mapping opening string to closing string",
        default_factory=lambda: {"(": ")"},
    )
    separators: Iterable[str] = dcfield(
        "Iterable of single character tokens that should be recognized as word separator",
        default=(";", "/", ","),
    )
    missing_data: Iterable[str] = dcfield(
        "Iterable of strings that are used to mark missing data",
        default=('?', '-'),
    )
    strip_inside_brackets: bool = dcfield(
        "Flag signaling whether to strip content in brackets "
        "(**and** strip leading and trailing whitespace)",
        default=True,
    )
    replacements: list[tuple[str, str]] = dcfield(
        "List of pairs (`source`, `target`) used to replace occurrences of `source` in forms"
        "with `target` (before stripping content in brackets)",
        default_factory=list,
    )
    first_form_only: bool = dcfield(
        "Flag signaling whether at most one form should be returned from `split` - "
        "effectively ignoring any spelling variants, etc.",
        default=False,
    )
    normalize_whitespace: bool = dcfield(
        "Flag signaling whether to normalize whitespace - stripping leading and trailing "
        "whitespace and collapsing multi-character whitespace to single spaces",
        default=True,
    )
    normalize_unicode: Optional[Literal['NFD', 'NFC']] = dcfield(
        "UNICODE normalization form to use for input of `split` (`None`, 'NFD' or 'NFC')",
        default=None,
    )

    def __post_init__(self):
        try:
            assert isinstance(self.brackets, dict)
            assert isinstance(self.missing_data, (tuple, list))
            assert isinstance(self.strip_inside_brackets, bool)
            assert isinstance(self.first_form_only, bool)
            assert isinstance(self.normalize_whitespace, bool)
            assert self.normalize_unicode in ['NFD', 'NFC', None], self.normalize_unicode
        except AssertionError as e:
            raise ValueError('Illegal type') from e

        if not isinstance(self.separators, str):
            if not isinstance(self.separators, (list, tuple)):
                raise ValueError('separators must be an iterable of single character strings')
            for v in self.separators:
                if (not isinstance(v, str)) or len(v) > 1:
                    raise ValueError('separators must be an iterable of single character strings')

        if not isinstance(self.replacements, list):
            raise ValueError('replacements must be list of pairs')
        for v in self.replacements:
            if not (isinstance(v, tuple)
                    and len(v) == 2
                    and isinstance(v[0], str)
                    and isinstance(v[1], str)):
                raise ValueError('replacements must be list of pairs')

    def as_markdown(self, dataset=None) -> str:
        """
        :return: Description of `FormSpec` in markdown.
        """
        res = ['## Specification of form manipulation\n']
        res.extend([line.strip() for line in self.__class__.__doc__.splitlines()])
        for field in dataclasses.fields(self.__class__):
            res.extend([
                f'- `{field.name}`: `{getattr(self, field.name)}`',
                f'  {field.metadata["help"]}'
            ])
        if dataset:
            if dataset.lexemes:
                res.extend([
                    '### Replacement of invalid lexemes\n',
                    f'Source lexemes may be impossible to interpret correctly. '
                    f'{len(dataset.lexemes)} such lexemes are listed in '
                    f'[`etc/lexemes.csv`](etc/lexemes.csv) and replaced as specified in this file.',
                ])

            if dataset.segments:
                res.extend([
                    '### Replacement of invalid segmentation\n',
                    f'Segments provided in the source data may not be valid according to CLTS. '
                    f'{len(dataset.segments)} such segments are listed in '
                    f'[`etc/segments.csv`](etc/segments.csv) and replaced as specified in this '
                    f'file.',
                ])
        return '\n'.join(res)

    def clean(self, form: str, item=None) -> Optional[str]:  # pylint: disable=W0613
        """
        Called when a row is added to a CLDF dataset.

        :param form:
        :return: None to skip the form, or the cleaned form as string.
        """
        if form not in self.missing_data:
            for source, target in self.replacements:
                form = form.replace(source, target)
            if self.strip_inside_brackets:
                form = text.strip_brackets(form, brackets=self.brackets)
            if self.normalize_whitespace:
                return re.sub(r'\s+', ' ', form.strip())
            return form
        return None

    def split(self, item, value, lexemes=None):
        """Splits lexemes as found in Value field."""
        lexemes = lexemes or {}
        if value in lexemes:
            log.debug('overriding via lexemes.csv: %r -> %r', value, lexemes[value])
            value = lexemes[value]
        if self.normalize_unicode:
            value = unicodedata.normalize(self.normalize_unicode, value)
        res = misc.nfilter(
            self.clean(form, item=item)
            for form in text.split_text_with_context(
                value, separators=self.separators, brackets=self.brackets))
        if self.first_form_only:
            return res[:1]
        return res
