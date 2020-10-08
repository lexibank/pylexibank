import re
import logging
import unicodedata

import attr
from clldutils import text
from clldutils import misc

__all__ = ['FormSpec']
log = logging.getLogger('pylexibank')


def valid_replacements(instance, attribute, value):
    if not isinstance(value, list):
        raise ValueError('replacements must be list of pairs')
    for v in value:
        if not (isinstance(v, tuple)
                and len(v) == 2
                and isinstance(v[0], str)
                and isinstance(v[1], str)):
            raise ValueError('replacements must be list of pairs')


def valid_separators(instance, attribute, value):
    if not isinstance(value, str):
        if not isinstance(value, (list, tuple)):
            raise ValueError('separators must be an iterable of single character strings')
        for v in value:
            if (not isinstance(v, str)) or len(v) > 1:
                raise ValueError('separators must be an iterable of single character strings')


def attrib(help, **kw):
    kw['metadata'] = dict(help=help)
    return attr.ib(**kw)


@attr.s
class FormSpec(object):
    """
    Specification of the value-to-form processing in Lexibank datasets:

    The value-to-form processing is divided into two steps, implemented as methods:
    - `FormSpec.split`: Splits a string into individual form chunks.
    - `FormSpec.clean`: Normalizes a form chunk.

    These methods use the attributes of a `FormSpec` instance to configure their behaviour.
    """
    brackets = attrib(
        "Pairs of strings that should be recognized as brackets, specified as `dict` "
        "mapping opening string to closing string",
        default={"(": ")"},
        validator=attr.validators.instance_of(dict),
    )
    separators = attrib(
        "Iterable of single character tokens that should be recognized as word separator",
        default=(";", "/", ","),
        validator=valid_separators,
    )
    missing_data = attrib(
        "Iterable of strings that are used to mark missing data",
        default=('?', '-'),
        validator=attr.validators.instance_of((tuple, list)),
    )
    strip_inside_brackets = attrib(
        "Flag signaling whether to strip content in brackets "
        "(**and** strip leading and trailing whitespace)",
        default=True,
        validator=attr.validators.instance_of(bool))
    replacements = attrib(
        "List of pairs (`source`, `target`) used to replace occurrences of `source` in forms"
        "with `target` (before stripping content in brackets)",
        default=attr.Factory(list),
        validator=valid_replacements)
    first_form_only = attrib(
        "Flag signaling whether at most one form should be returned from `split` - "
        "effectively ignoring any spelling variants, etc.",
        default=False,
        validator=attr.validators.instance_of(bool),
    )
    normalize_whitespace = attrib(
        "Flag signaling whether to normalize whitespace - stripping leading and trailing "
        "whitespace and collapsing multi-character whitespace to single spaces",
        default=True,
        validator=attr.validators.instance_of(bool),
    )
    normalize_unicode = attrib(
        "UNICODE normalization form to use for input of `split` (`None`, 'NFD' or 'NFC')",
        default=None,
        validator=attr.validators.in_(['NFD', 'NFC', None]),
    )

    def as_markdown(self, dataset=None):
        """
        :return: Description of `FormSpec` in markdown.
        """
        res = ['## Specification of form manipulation\n']
        res.extend([line.strip() for line in self.__class__.__doc__.splitlines()])
        for field in attr.fields(self.__class__):
            res.extend([
                '- `{0}`: `{1}`'.format(field.name, getattr(self, field.name)),
                '  {0}'.format(field.metadata['help'])
            ])
        if dataset:
            if dataset.lexemes:
                res.append("""
### Replacement of invalid lexemes

Source lexemes may be impossible to interpret correctly. {0} such lexemes are listed
in [`etc/lexemes.csv`](etc/lexemes.csv) and replaced as specified in this file.
""".format(len(dataset.lexemes)))

            if dataset.segments:
                res.append("""
### Replacement of invalid segmentation

Segments provided in the source data may not be valid according to CLTS.
{0} such segments are listed in [`etc/segments.csv`](etc/segments.csv) and replaced
as specified in this file.
""".format(len(dataset.segments)))
        return '\n'.join(res)

    def clean(self, form, item=None):
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

    def split(self, item, value, lexemes=None):
        lexemes = lexemes or {}
        if value in lexemes:
            log.debug('overriding via lexemes.csv: %r -> %r' % (value, lexemes[value]))
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
