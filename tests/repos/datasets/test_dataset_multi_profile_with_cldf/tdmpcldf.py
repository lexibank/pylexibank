from pathlib import Path

from pylexibank import Dataset


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset_multi_profiles_with_cldf'
