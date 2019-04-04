import logging
import re
import zipfile
from collections import OrderedDict
from xml.etree import cElementTree as et
from contextlib import contextmanager

import requests
import requests.packages.urllib3
from termcolor import colored
import xlrd
from tqdm import tqdm

from clldutils.dsv import UnicodeWriter, reader
from clldutils.path import (
    Path, as_posix, copy, TemporaryDirectory, git_describe, remove,
    read_text, write_text,
)
from clldutils.misc import slug, xmlchars
from clldutils.badge import Colors, badge
from clldutils import jsonlib
from pycldf.sources import Source, Reference
from pybtex import database
import pylexibank

requests.packages.urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)
REPOS_PATH = Path(pylexibank.__file__).parent.parent
YEAR_PATTERN = re.compile('\s+\(?(?P<year>[1-9][0-9]{3}(-[0-9]+)?)(\)|\.)')


def aligned(pairs):
    maxlabel = max(len(p[0]) for p in pairs)
    return '\n'.join('  {0} {1}'.format(p[0].ljust(maxlabel), p[1] or '') for p in pairs)


def git_hash(d):
    return git_describe(d).split('-g')[-1]


def pb(iterable=None, **kw):
    kw.setdefault('leave', False)
    return tqdm(iterable=iterable, **kw)


class Repos(object):
    @property
    def version(self):
        return git_describe(self.repos)


def split_by_year(s):
    match = YEAR_PATTERN.search(s)
    if match:
        return s[:match.start()].strip(), match.group('year'), s[match.end():].strip()
    return None, None, s


def get_reference(author, year, title, pages, sources, id_=None, genre='misc'):
    kw = {'title': title}
    id_ = id_ or None
    if author and year:
        id_ = id_ or slug(author + year)
        kw.update(author=author, year=year)
    elif title:
        id_ = id_ or slug(title)

    if not id_:
        return

    source = sources.get(id_)
    if source is None:
        sources[id_] = source = Source(genre, id_, **kw)

    return Reference(source, pages)


def data_path(*comps, **kw):
    return kw.get('repos', REPOS_PATH).joinpath('datasets', *comps)


def get_badge(ratio, name):
    if ratio >= 0.99:
        color = Colors.brightgreen
    elif ratio >= 0.9:
        color = 'green'
    elif ratio >= 0.8:
        color = Colors.yellowgreen
    elif ratio >= 0.7:
        color = Colors.yellow
    elif ratio >= 0.6:
        color = Colors.orange
    else:
        color = Colors.red
    ratio = int(round(ratio * 100))
    return badge(name, '%s%%' % ratio, color, label="{0}: {1}%".format(name, ratio))


def sorted_obj(obj):
    res = obj
    if isinstance(obj, dict):
        res = OrderedDict()
        obj.pop(None, None)
        for k, v in sorted(obj.items()):
            res[k] = sorted_obj(v)
    elif isinstance(obj, (list, set)):
        res = [sorted_obj(v) for v in obj]
    return res


def log_dump(fname, log=None):
    if log:
        log.info('file written: {0}'.format(colored(fname.as_posix(), 'green')))


def jsondump(obj, fname, log=None):
    fname = Path(fname)
    if fname.exists():
        d = jsonlib.load(fname)
        d.update(obj)
        obj = d
    jsonlib.dump(sorted_obj(obj), fname, indent=4)
    log_dump(fname, log=log)
    return obj


def textdump(text, fname, log=None):
    if isinstance(text, list):
        text = '\n'.join(text)
    with fname.open('w', encoding='utf8') as fp:
        fp.write(text)
    log_dump(fname, log=log)


def get_url(url, log=None, **kw):
    res = requests.get(url, **kw)
    if log:
        level = log.info if res.status_code == 200 else log.warn
        level('HTTP {0} for {1}'.format(
            colored(res.status_code, 'blue'), colored(url, 'blue')))
    return res


class DataDir(type(Path())):
    def posix(self, *comps):
        return self.joinpath(*comps).as_posix()

    def read(self, fname, encoding='utf8'):
        return read_text(self.joinpath(fname), encoding=encoding)

    def write(self, fname, text, encoding='utf8'):
        write_text(self.joinpath(fname), text, encoding=encoding)
        return fname

    def remove(self, fname):
        remove(self.joinpath(fname))

    def read_csv(self, fname, **kw):
        return list(reader(self.joinpath(fname), **kw))

    def read_tsv(self, fname, **kw):
        return self.read_csv(fname, delimiter='\t', **kw)

    def read_xml(self, fname, wrap=True):
        xml = xmlchars(self.read(fname))
        if wrap:
            xml = '<r>{0}</r>'.format(xml)
        return et.fromstring(xml.encode('utf8'))

    def read_json(self, fname, **kw):
        return jsonlib.load(fname)

    def read_bib(self, fname='sources.bib'):
        bib = database.parse_string(self.read(fname), bib_format='bibtex')
        return [Source.from_entry(k, e) for k, e in bib.entries.items()]

    def xls2csv(self, fname, outdir=None):
        if isinstance(fname, str):
            fname = self.joinpath(fname)
        res = {}
        outdir = outdir or self
        wb = xlrd.open_workbook(fname.as_posix())
        for sname in wb.sheet_names():
            sheet = wb.sheet_by_name(sname)
            if sheet.nrows:
                path = outdir.joinpath(
                    fname.stem + '.' + slug(sname, lowercase=False) + '.csv')
                with UnicodeWriter(path) as writer:
                    for i in range(sheet.nrows):
                        writer.writerow([col.value for col in sheet.row(i)])
                res[sname] = path
        return res

    @contextmanager
    def temp_download(self, url, fname, log=None):
        p = None
        try:
            p = self.download(url, fname, log=log)
            yield p
        finally:
            if p and p.exists():
                remove(p)

    def download(self, url, fname, log=None, skip_if_exists=False):
        p = self.joinpath(fname)
        if p.exists() and skip_if_exists:
            return p
        res = get_url(url, log=log, stream=True)
        with open(self.posix(fname), 'wb') as fp:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    fp.write(chunk)
        return p

    def download_and_unpack(self, url, *paths, **kw):
        """
        Download a zipfile and immediately unpack selected content.

        :param url:
        :param paths:
        :param kw:
        :return:
        """
        with self.temp_download(url, 'ds.zip', log=kw.pop('log', None)) as zipp:
            with TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(zipp.as_posix()) as zipf:
                    for path in paths:
                        zipf.extract(as_posix(path), path=tmpdir.as_posix())
                        copy(tmpdir.joinpath(path), self)


def getEvoBibAsBibtex(*keys, **kw):
    """Download bibtex format and parse it from EvoBib"""
    res = []
    for key in keys:
        bib = get_url(
            "http://bibliography.lingpy.org/raw.php?key=" + key,
            log=kw.get('log')).text
        try:
            res.append('@' + bib.split('@')[1].split('</pre>')[0])
        except IndexError:  # pragma: no cover
            res.append('@misc{' + key + ',\nNote={missing source}\n\n}')
    return '\n\n'.join(res)
