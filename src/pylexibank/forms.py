import logging

import attr
from clldutils import text
from clldutils import misc

__all__ = ['FormSpec', 'FirstFormOnlySpec']
log = logging.getLogger('pylexibank')


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

    def clean(self, form, item=None):
        """
        Called when a row is added to a CLDF dataset.

        :param form:
        :return: None to skip the form, or the cleaned form as string.
        """
        if form not in self.missing_data:
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
