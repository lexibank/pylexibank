from zipfile import ZipFile

from clldutils.path import remove, read_text
from clldutils.misc import lazyproperty
from pycldf import Wordlist
from pycldf.dataset import MD_SUFFIX

from pylexibank.dataset import Dataset


class CLLD(Dataset):
    __cldf_url__ = None

    def url(self, path='/'):
        return "http://{0}.clld.org{1}".format(self.id, path)

    def cmd_download(self, **kw):
        zname = '{0}.zip'.format(self.id)
        self.raw.download(self.__cldf_url__, zname, log=self.log)
        archive = ZipFile(str(self.raw / zname))
        archive.extractall(str(self.raw))
        remove(self.raw / zname)

    def add_sources(self, ds):
        ds.add_sources(read_text(self.raw / 'sources.bib'))

    @lazyproperty
    def original_cldf(self):
        for p in self.raw.iterdir():
            if p.name.endswith(MD_SUFFIX):
                return Wordlist.from_metadata(p)
