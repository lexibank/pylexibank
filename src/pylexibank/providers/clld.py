import zipfile

from clldutils.misc import lazyproperty
from pycldf import Wordlist
from pycldf.dataset import MD_SUFFIX

from pylexibank.dataset import Dataset


class CLLD(Dataset):
    __cldf_url__ = None

    def url(self, path='/'):
        return "http://{0}.clld.org{1}".format(self.id, path)

    def cmd_download(self, args):
        zname = '{0}.zip'.format(self.id)
        self.raw_dir.download(self.__cldf_url__, zname, log=args.log)
        archive = zipfile.ZipFile(str(self.raw_dir / zname))
        archive.extractall(str(self.raw_dir))
        (self.raw_dir / zname).unlink()

    def add_sources(self, ds):
        ds.add_sources((self.raw_dir / 'sources.bib').read_text(encoding='utf8'))

    @lazyproperty
    def original_cldf(self):
        for p in self.raw_dir.iterdir():
            if p.name.endswith(MD_SUFFIX):
                return Wordlist.from_metadata(p)
