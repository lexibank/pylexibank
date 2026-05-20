"""
Utility functions
"""
import re
import logging
import pathlib
import itertools
import collections
from collections.abc import Iterable, Generator
from typing import Union, Callable, Any, Optional

from termcolor import colored
from tqdm import tqdm

from clldutils.misc import slug
from clldutils import jsonlib
from pycldf.sources import Source, Reference
from pyconcepticon.api import Concept, Conceptlist

__all__ = ['progressbar', 'iter_repl']
ENTRY_POINT = 'lexibank.dataset'
YEAR_PATTERN = re.compile(r'\s+\(?(?P<year>[1-9][0-9]{3}(-[0-9]+)?)(\)|\.)')


def progressbar(iterable=None, **kw):
    """A suitable initialized tqdm progressbar."""
    kw.setdefault('leave', False)
    kw.setdefault('desc', 'cldfbench')
    return tqdm(iterable=iterable, **kw)


# backwards compat:
pb = progressbar


def iter_repl(seq, subseq, repl) -> Generator[Any, None, None]:
    """
    Replace sub-list `subseq` in `seq` with `repl`.

    >>> list(iter_repl('abcdefgabcdef', 'bcd', 'X'))
    ['a', 'X', 'e', 'f', 'g', 'a', 'X', 'e', 'f']
    """
    seq, subseq, repl = list(seq), list(subseq), list(repl)
    subseq_len = len(subseq)
    rem = seq[:]
    while rem:
        if rem[:subseq_len] == subseq:
            yield from repl
            rem = rem[subseq_len:]
        else:
            yield rem.pop(0)


def split_by_year(s: str) -> tuple[Optional[str], Optional[str], str]:
    """Split a string by what looks like a year, returning prefix, match and remainder."""
    match = YEAR_PATTERN.search(s)
    if match:
        return s[:match.start()].strip(), match.group('year'), s[match.end():].strip()
    return None, None, s


def get_reference(  # pylint: disable=R0913,R0917
        author: Optional[str],
        year: Optional[str],
        title: Optional[str],
        pages: Optional[str],
        sources: dict[str, Source],
        id_: Optional[str] = None,
        genre: str = 'misc',
) -> Optional[Reference]:
    """Get a Reference object for citation data."""
    kw = {'title': title}
    id_ = id_ or None
    if author and year:
        id_ = id_ or slug(author + year)
        kw.update(author=author, year=year)
    elif title:
        id_ = id_ or slug(title)

    if not id_:
        return None

    source = sources.get(id_)
    if source is None:
        sources[id_] = source = Source(genre, id_, **kw)

    return Reference(source, pages)


def sorted_obj(obj: Union[list, dict, set, Any]) -> Union[dict, list, Any]:
    """
    Sort obj if possible, recursively for some container types.

    Sorted results of operations can be compared better.
    """
    if isinstance(obj, dict):
        res = collections.OrderedDict()
        obj.pop(None, None)
        for k, v in sorted(obj.items()):
            # Fix weirdly dictified collection.Counter from dataclasses.asdict.
            if isinstance(k, tuple) and isinstance(k[1], int) and v == 1:
                k, v = k
            res[k] = sorted_obj(v)
        return res
    if isinstance(obj, (list, set)):
        return [sorted_obj(v) for v in obj]
    return obj


def log_dump(fname: pathlib.Path, log: Optional[logging.Logger] = None):
    """Maybe log that a file was written."""
    if log:
        log.info('file written: %s', colored(fname.as_posix(), 'green'))


def jsondump(
        obj: dict[str, Any],
        fname: Union[str, pathlib.Path],
        log: Optional[logging.Logger] = None,
) -> dict[str, Any]:
    """Dump obj to a JSON file. If the file exists, the contained object will be updated."""
    fname = pathlib.Path(fname)
    if fname.exists():
        d = jsonlib.load(fname)
        d.update(obj)
        obj = d
    jsonlib.dump(sorted_obj(obj), fname, indent=4)
    log_dump(fname, log=log)
    return obj


def get_concepts(conceptlists: Iterable[Conceptlist], concepts: Iterable[dict]) -> list[Concept]:
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


def get_ids_and_attrs(
        concepts: list[Concept],
        fieldnames: dict[str, str],
        id_factory: Union[str, Callable[[Union[Concept, dict[str, Any]]], str]],
        lookup_factory: Union[None, str, Callable[[Union[Concept, dict[str, Any]]], str]],
) -> tuple[collections.OrderedDict[str, str], list[dict[str, Any]]]:
    """
    Get concept IDs and sets of standard metadata for concepts, abstracting away whether the
    concepts of the dataset come from the Concepticon API or a local CSV file.
    """
    id_lookup, objs = collections.OrderedDict(), []

    for i, c in enumerate(concepts):
        try:
            # `id_factory` might expect a pyconcepticon.Concept instance as input:
            id_ = id_factory(c) if callable(id_factory) else getattr(c, id_factory)
        except AttributeError:
            id_ = None
        attrs = dict(  # pylint: disable=R1735
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
