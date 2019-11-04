import logging

import attr
from clldutils import text
from clldutils import misc

__all__ = ['FormSpec', 'FirstFormOnlySpec']
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


@attr.s
class FormSpec(object):
    brackets = attr.ib(
        default={"(": ")"},
        validator=attr.validators.instance_of(dict))
    separators = attr.ib(default=";/,")
    missing_data = attr.ib(
        default=('?', '-'),
        validator=attr.validators.instance_of((tuple, list)))
    strip_inside_brackets = attr.ib(
        default=True,
        validator=attr.validators.instance_of(bool))
    replacements = attr.ib(
        default=attr.Factory(list),
        validator=valid_replacements)

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
                return text.strip_brackets(form, brackets=self.brackets)
            return form

    def split(self, item, value, lexemes=None):
        lexemes = lexemes or {}
        if value in lexemes:
            log.debug('overriding via lexemes.csv: %r -> %r' % (value, lexemes[value]))
            value = lexemes[value]
        return misc.nfilter(
            self.clean(form, item=item)
            for form in text.split_text_with_context(
                value, separators=self.separators, brackets=self.brackets))


@attr.s
class FirstFormOnlySpec(FormSpec):
    def split(self, *args, **kw):
        return super().split(*args, **kw)[:1]
