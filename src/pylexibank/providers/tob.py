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
        return 'http://starling.rinet.ru/cgi-bin/response.cgi?' + \
            'root=new100&morpho=0&basename=new100' + \
            r'\{0}\{1}&first={2}'.format(self.dset, self.name, page)

    def cmd_download(self, args):
        self.raw_dir.write('sources.bib', "\n".join(self.tob_sources.values()))

        # download data
        all_records = []
        for i in pb(list(range(1, 20 * self.pages + 1, 20))):
            with self.raw_dir.temp_download(
                    self._url(i), 'file-{0}'.format(i), log=args.log) as fname:
                soup = BeautifulSoup(fname.open(encoding='utf8').read(), 'html.parser')
                for record in soup.findAll(name='div', attrs={"class": "results_record"}):
                    if isinstance(record, bs4.element.Tag):
                        children = list(record.children)
                        number = children[0].findAll('span')[1].text.strip()
                        concept = children[1].findAll('span')[1].text
                        for child in children[2:]:
                            if isinstance(child, bs4.element.Tag):
                                dpoints = child.findAll('span')
                                if len(dpoints) >= 3:
                                    lname = dpoints[1].text
                                    glottolog = re.findall(
                                        'Glottolog: (........)', str(dpoints[1]))[0]
                                    entry = dpoints[2].text
                                    cogid = list(child.children)[4].text.strip()
                                    all_records.append(
                                        (number, concept, lname, glottolog, entry, cogid))
        with UnicodeWriter(self.raw_dir / 'output.csv') as f:
            f.writerows(all_records)

    def cmd_makecldf(self, args):
        args.writer.add_sources()
        concepts = args.writer.add_concepts(
            id_factory=lambda c: c.id.split('-')[-1] + '_' + slug(c.english),
            lookup_factory=lambda c: c.id.split('-')[-1]
        )
        for cid, concept, lang, gc, form, cogid in self.raw_dir.read_csv('output.csv'):
            lid = lang.replace(' ', '_')
            args.writer.add_language(ID=lid, Name=lang, Glottocode=gc)
            global_cog_id = "%s-%s" % (cid, cogid)
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
