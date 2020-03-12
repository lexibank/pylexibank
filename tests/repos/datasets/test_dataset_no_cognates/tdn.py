import pathlib

from pylexibank import Dataset


class Test(Dataset):
    dir = pathlib.Path(__file__).parent
    id = 'test_dataset_no_cognates'
    github_repo = 'x/y'

    def cmd_makecldf(self, args):
        args.writer.add_sources('@book{abc,\ntitle={The Title}\n}')
        args.writer.add_language(ID='lang1', Glottocode='abcd1234')
        args.writer.add_concept(ID='param1', Concepticon_ID=1)
        args.writer.add_lexemes(Language_ID='lang1', Parameter_ID='param1', Value='a b; c')
