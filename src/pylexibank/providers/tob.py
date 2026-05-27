"""
Tower-Of-Babel, aka starling as lexibank data provider.
"""
import re
from textwrap import dedent

from bs4 import BeautifulSoup
import bs4
from csvw.dsv import UnicodeWriter
from clldutils.misc import slug

from pylexibank.dataset import Dataset
from pylexibank.forms import FormSpec
from pylexibank.util import pb


class TOB(Dataset):
    """A dataset based on data from the Tower-Of-Babel project."""
    name = None
    dset = None
    pages = 1
    lexemes = {}

    form_spec = FormSpec(
        brackets={"(": ")"},
        separators=";/,~",
        missing_data=('?', '-', ''),
        strip_inside_brackets=True
    )

    tob_sources = {
        "Starostin2011": dedent("""
        @misc{Starostin2011,
            Year = {2011},
            Editor = {Starostin, George S. and Krylov, Phil},
            Title = {The Global Lexicostatistical Database}
        }""")
    }

    def _url(self, page):
        # https://starlingdb.org/cgi-bin/response.cgi
        return (f'http://starling.rinet.ru/cgi-bin/response.cgi'
                f'?root=new100&morpho=0&basename=new100\\{self.dset}\\{self.name}&first={page}')

    def cmd_download(self, args):
        self.raw_dir.write('sources.bib', "\n".join(self.tob_sources.values()))

        # download data
        all_records = []
        for i in pb(list(range(1, 20 * self.pages + 1, 20))):
            with self.raw_dir.temp_download(self._url(i), f'file-{i}', log=args.log) as fname:
                soup = BeautifulSoup(fname.open(encoding='utf8').read(), 'html.parser')
                for record in soup.find_all(name='div', attrs={"class": "results_record"}):
                    if isinstance(record, bs4.element.Tag):
                        children = list(record.children)
                        number = children[0].find_all('span')[1].text.strip()
                        concept = children[1].find_all('span')[1].text
                        for child in children[2:]:
                            if isinstance(child, bs4.element.Tag):
                                dpoints = child.find_all('span')
                                if len(dpoints) >= 3:
                                    all_records.append((
                                        number,
                                        concept,
                                        dpoints[1].text,  # Language name
                                        re.findall('Glottolog: (........)', str(dpoints[1]))[0],
                                        dpoints[2].text,  # Entry
                                        list(child.children)[4].text.strip(),  # cogid
                                    ))
        with UnicodeWriter(self.raw_dir / 'output.csv') as f:
            f.writerows(all_records)

    def cmd_makecldf(self, args):
        args.writer.add_sources()
        concepts = args.writer.add_concepts(
            id_factory=lambda c: c.id.split('-')[-1] + '_' + slug(c.english),
            lookup_factory=lambda c: c.id.split('-')[-1]
        )
        for cid, _, lang, gc, form, cogid in self.raw_dir.read_csv('output.csv'):
            lid = lang.replace(' ', '_')
            args.writer.add_language(ID=lid, Name=lang, Glottocode=gc)
            global_cog_id = f"{cid}-{cogid}"
            for row in args.writer.add_forms_from_value(
                Language_ID=lid,
                Parameter_ID=concepts[cid],
                Value=form,
                Source=list(self.tob_sources),
                Cognacy=global_cog_id
            ):
                args.writer.add_cognate(
                    lexeme=row,
                    Cognateset_ID=global_cog_id,
                    Source=list(self.tob_sources))
