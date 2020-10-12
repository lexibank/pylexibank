import re
import pathlib
import itertools
import collections

from termcolor import colored
from tqdm import tqdm

from clldutils.misc import slug
from clldutils.badge import Colors, badge
from clldutils import jsonlib
from cldfbench.datadir import get_url
from pycldf.sources import Source, Reference
from pyconcepticon.api import Concept

__all__ = ['progressbar', 'getEvoBibAsBibtex', 'iter_repl']
YEAR_PATTERN = re.compile(r'\s+\(?(?P<year>[1-9][0-9]{3}(-[0-9]+)?)(\)|\.)')


def progressbar(iterable=None, **kw):
    kw.setdefault('leave', False)
    kw.setdefault('desc', 'cldfbench')
    return tqdm(iterable=iterable, **kw)


# backwards compat:
pb = progressbar


def iter_repl(seq, subseq, repl):
    """
    Replace sub-list `subseq` in `seq` with `repl`.
    """
    seq, subseq, repl = list(seq), list(subseq), list(repl)
    subseq_len = len(subseq)
    rem = seq[:]
    while rem:
        if rem[:subseq_len] == subseq:
            for c in repl:
                yield c
            rem = rem[subseq_len:]
        else:
            yield rem.pop(0)


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
        res = collections.OrderedDict()
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
    fname = pathlib.Path(fname)
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
            raise KeyError('Missing entry {0} in evobib'.format(key))
    return '\n\n'.join(res)


def get_concepts(conceptlists, concepts):
    """
    Read pyconcepticon.Concept instances either from a conceptlist in Concepticon, or from
    etc/concepts.csv:

    :param conceptlists:
    :param concepts:
    :return:
    """
    if conceptlists:
        return list(itertools.chain(*[cl.concepts.values() for cl in conceptlists]))

    res = []
    fields = Concept.public_fields()
    for i, concept in enumerate(concepts, start=1):
        kw, attrs = {}, {}
        for k, v in concept.items():
            if k.lower() in fields:
                kw[k.lower()] = v
            else:
                attrs[k.lower()] = v

        if not kw.get('id'):
            kw['id'] = str(i)
        if not kw.get('number'):
            kw['number'] = str(i)
        res.append(Concept(attributes=attrs, **kw))
    return res


def get_ids_and_attrs(concepts, fieldnames, id_factory, lookup_factory):
    id_lookup, objs = collections.OrderedDict(), []

    for i, c in enumerate(concepts):
        try:
            # `id_factory` might expect a pyconcepticon.Concept instance as input:
            id_ = id_factory(c) if callable(id_factory) else getattr(c, id_factory)
        except AttributeError:
            id_ = None
        attrs = dict(
            ID=id_,
            Name=c.label,
            Concepticon_ID=c.concepticon_id,
            Concepticon_Gloss=c.concepticon_gloss)
        for fl, f in fieldnames.items():
            if f not in attrs:
                if fl in c.attributes:
                    attrs[f] = c.attributes[fl]
                if hasattr(c, fl):
                    attrs[f] = getattr(c, fl)
        if attrs['ID'] is None:
            attrs['ID'] = id_factory(attrs) if callable(id_factory) else attrs[id_factory]
        if lookup_factory is None:
            key = i
        else:
            try:
                key = lookup_factory(attrs) if callable(lookup_factory) else attrs[lookup_factory]
            except (KeyError, AttributeError):
                key = lookup_factory(c) if callable(lookup_factory) else getattr(c, lookup_factory)
        id_lookup[key] = attrs['ID']
        objs.append(attrs)

    return id_lookup, objs
