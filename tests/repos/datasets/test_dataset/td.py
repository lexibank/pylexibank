from pathlib import Path
from clldutils.misc import lazyproperty
import attr

from pylexibank import Dataset, Concept


@attr.s
class TestConcept(Concept):
    Chinese = attr.ib(default=None)


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset'
    concept_class = TestConcept
    github_repo = 'x/y'

    @lazyproperty
    def tokenizer(self):
        from lingpy.sequence.sound_classes import clean_string
        return lambda _, s, **kw: clean_string(s)

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        from pylexibank.lingpy_util import iter_cognates
        args.writer.add_sources()
        args.writer.add_sources('@book{abc,\ntitle={The Title}\n}')
        args.writer.add_languages()
        args.writer.add_language(ID='lang1', Glottocode='abcd1234')
        args.writer.add_language(ID='lang2')
        args.writer.add_concepts(lookup_factory='Chinese', id_factory='Concepticon_ID')
        args.writer.add_concept(ID='param1', Concepticon_ID=1)
        args.writer.add_concept(ID='param2')
        for l in args.writer.add_lexemes(
            Language_ID='lang1',
            Parameter_ID='param1',
            Value='a b; c'
        ):
            args.writer.add_cognate(lexeme=l, Cognateset_ID='c-1')
        args.writer.add_lexemes(
            Language_ID='lang1',
            Parameter_ID='param1',
            Value='a^b',
            Source=['abc'],
        )
        args.writer.add_lexemes(
            Language_ID='lang1',
            Parameter_ID='param1',
            Value='^^^'
        )
        args.writer.add_lexemes(
            Language_ID='lang2',
            Parameter_ID='param2',
            Value='a~b')
        args.writer.add_form_with_segments(
            Language_ID='lang2',
            Parameter_ID='param2',
            Value='a~b-c',
            Form='ab',
            Segments=['+', 'a', '+ +', 'b', '+'],
        )
        try:
            list(iter_cognates(args.writer))
        except ValueError:
            pass
        try:
            list(iter_cognates(args.writer, method='sca'))
        except ValueError:
            pass
