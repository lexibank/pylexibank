from pathlib import Path

from pylexibank.dataset import Dataset


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset_cldf'

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        pass
