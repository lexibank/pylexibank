import re
from collections import OrderedDict
from pathlib import Path

from termcolor import colored
from tqdm import tqdm

from clldutils.misc import slug
from clldutils.badge import Colors, badge
from clldutils import jsonlib
from cldfbench.datadir import get_url
from pycldf.sources import Source, Reference

__all__ = ['progressbar', 'getEvoBibAsBibtex']
YEAR_PATTERN = re.compile('\s+\(?(?P<year>[1-9][0-9]{3}(-[0-9]+)?)(\)|\.)')


def progressbar(iterable=None, **kw):
    kw.setdefault('leave', False)
    kw.setdefault('desc', 'cldfbench')
    return tqdm(iterable=iterable, **kw)


# backwards compat:
pb = progressbar


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
