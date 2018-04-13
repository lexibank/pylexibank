# coding: utf8
from __future__ import unicode_literals, print_function, division

from pylexibank.dataset import Dataset


class QLC(Dataset):
    DSETS = []

    #def cmd_download(self, **kw):
    #    self.raw.download_and_unpack(
    #        "http://www.quanthistling.info/data/downloads/csv/data.zip",
    #        *[name for name in self.DSETS],
    #        **{'log': self.log})
