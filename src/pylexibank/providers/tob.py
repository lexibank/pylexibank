# coding: utf8
from __future__ import unicode_literals, print_function, division
import re

from six import text_type
from bs4 import BeautifulSoup
import bs4
from clldutils.dsv import UnicodeWriter

from pylexibank.dataset import Dataset
from pylexibank.util import pb, getEvoBibAsBibtex


class TOB(Dataset):
    name = None
    dset = None
    pages = 1
    lexemes = {}

    def _url(self, page):
        return 'http://starling.rinet.ru/cgi-bin/response.cgi?' + \
            'root=new100&morpho=0&basename=new100' + \
            r'\{0}\{1}&first={2}'.format(self.dset, self.name, page)

    def cmd_download(self, **kw):
        # download source
        self.raw.write('sources.bib', getEvoBibAsBibtex('Starostin2011', **kw))
        
        # download data
        all_records = []
        for i in pb(list(range(1, 20 * self.pages+1, 20))):
            with self.raw.temp_download(
                    self._url(i), 'file-{0}'.format(i), log=self.log) as fname:
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
                                        'Glottolog: (........)', text_type(dpoints[1]))[0]
                                    entry = dpoints[2].text
                                    cogid = list(child.children)[4].text.strip()
                                    all_records.append(
                                        (number, concept, lname, glottolog, entry, cogid))
        with UnicodeWriter(self.raw.posix('output.csv')) as f:
            f.writerows(all_records)

    def cmd_install(self, *args, **kw):
        cognate_source = self.raw.read_bib()[0]
        concepticon = {
            c.number: c.concepticon_id for c in self.conceptlist.concepts.values()}

        with self.cldf as ds:
            for cid, concept, lid, gc, form, cogid in pb(self.raw.read_csv('output.csv')):
                ds.add_language(ID=lid, Name=lid, Glottocode=gc)
                ds.add_concept(ID=cid, Name=concept, Concepticon_ID=concepticon[cid])
                for row in ds.add_lexemes(
                    Language_ID=lid,
                    Parameter_ID=cid,
                    Value=form,
                    Cognacy=concept+'-'+cogid
                ):
                    ds.add_cognate(
                        lexeme=row,
                        Cognateset_ID=cogid,
                        Source=[cognate_source.id])
