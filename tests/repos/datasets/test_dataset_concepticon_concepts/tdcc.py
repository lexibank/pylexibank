import pathlib

from pylexibank import Dataset, CONCEPTICON_CONCEPTS


class Test(Dataset):
    dir = pathlib.Path(__file__).parent
    id = 'test_dataset_concepticon_concepts'
    concept_class = CONCEPTICON_CONCEPTS

    def cmd_makecldf(self, args):
        args.writer.add_sources('@book{abc,\ntitle={The Title}\n}')
        args.writer.add_language(ID='lang1', Glottocode='abcd1234')
        id_map = args.writer.add_concepts(lookup_factory='CHINESE')
        args.writer.add_lexemes(Language_ID='lang1', Parameter_ID=id_map['天'], Value='a b; c')
