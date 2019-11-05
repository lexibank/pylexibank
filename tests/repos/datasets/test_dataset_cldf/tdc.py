from pathlib import Path

from pylexibank.dataset import Dataset


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset_cldf'

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        args.writer.add_language(ID='l')
        args.writer.add_concepts()
        args.writer.add_form_with_segments(
            Language_ID='l',
            Parameter_ID='1',
            Value='__',
            Form='__',
            Segments=[' ', ' '],  # This should trigger marking as invalid_word
        )
