# coding: utf8
from __future__ import unicode_literals, print_function, division
from zipfile import ZipFile

from clldutils.dsv import reader
from clldutils.path import TemporaryDirectory, write_text
from pycldf.dataset import MD_SUFFIX

from pylexibank.dataset import Dataset
from pylexibank.util import pb


class CLLD(Dataset):
    __cldf_url__ = None

    def url(self, path='/'):
        return "http://{0}.clld.org{1}".format(self.id, path)

    def cmd_download(self, **kw):
        self.raw.download(self.__cldf_url__, '{0}.zip'.format(self.id), log=self.log)
        self.raw.download(
            self.url(path="/resourcemap.json?rsc=language"),
            'languages.json',
            log=self.log)

    def add_sources(self, ds):
        archive = ZipFile(self.raw.joinpath('{0}.zip'.format(self.id)).as_posix())
        for name in archive.namelist():
            if name.endswith('.bib'):
                ds.add_sources(archive.read(name).decode('utf8'))

    def iteritems(self):
        archive = ZipFile(self.raw.joinpath('{0}.zip'.format(self.id)).as_posix())
        names = [name[:-len(MD_SUFFIX)]
                 for name in archive.namelist() if name.endswith(MD_SUFFIX)]
        with TemporaryDirectory() as tmp:
            for name in pb(names):
                write_text(tmp.joinpath('csv'), archive.read(name).decode('utf8'))
                for item in reader(tmp.joinpath('csv'), dicts=True):
                    item['Source'] = [item['Source']]
                    yield item
