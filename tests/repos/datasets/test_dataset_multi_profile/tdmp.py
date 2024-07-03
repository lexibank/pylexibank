from pathlib import Path

from pylexibank import Dataset


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset_multi_profiles'
    writer_options = dict(keep_languages=False, keep_parameters=False)

    def cmd_makecldf(self, args):
        args.writer.add_sources('@book{abc,\ntitle={The Title}\n}')
        args.writer.add_language(ID='lang1', Glottocode='abcd1234')
        args.writer.add_concept(ID='param1', Concepticon_ID=1)
        args.writer.add_language(ID='lang2', Glottocode='abcd1234')
        args.writer.add_concept(ID='param2', Concepticon_ID=1)

        for form in args.writer.add_lexemes(
                Language_ID='lang1',
                Parameter_ID='param1',
                Value='a',
                Source=['abc'],
                profile='p1',
        ):
            assert form['Segments'] == ['b']

        for form in args.writer.add_lexemes(
            Language_ID='lang1',
            Parameter_ID='param1',
            Value='a',
            Source=['abc'],
            profile='p2',
        ):
            assert form['Segments'] == ['c']
