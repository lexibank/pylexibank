# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path

from pylexibank.dataset import Dataset


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset_cldf'

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        pass
