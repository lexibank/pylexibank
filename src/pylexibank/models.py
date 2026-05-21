"""
Functionality to represent data to be added as rows to CLDF tables using dataclasses.
"""
from collections.abc import Iterable
import dataclasses
from typing import Optional

from pyconcepticon.models import Conceptlist

__all__ = [
    'Language', 'Lexeme', 'Concept', 'Cognate', 'CONCEPTICON_CONCEPTS', 'concepticon_concepts']

CONCEPTICON_CONCEPTS = 1


@dataclasses.dataclass
class FieldnamesMixin:  # pylint: disable=R0903,C0115
    @classmethod
    def fieldnames(cls):
        """Shortcut to access the fieldnames from the class of an instance."""
        return [f.name for f in dataclasses.fields(cls)]


@dataclasses.dataclass
class Language(FieldnamesMixin):  # pylint: disable=R0902
    """A language."""
    ID: str = ''  # pylint: disable=C0103
    Name: Optional[str] = None  # pylint: disable=C0103
    ISO639P3code: Optional[str] = None  # pylint: disable=C0103
    Glottocode: Optional[str] = None  # pylint: disable=C0103
    Macroarea: Optional[str] = None  # pylint: disable=C0103
    Latitude: Optional[float] = None  # pylint: disable=C0103
    Longitude: Optional[float] = None  # pylint: disable=C0103
    Glottolog_Name: Optional[str] = None  # pylint: disable=C0103
    Family: Optional[str] = None  # pylint: disable=C0103

    def __hash__(self):
        return hash(self.ID)

    @classmethod
    def __cldf_table__(cls):
        return 'LanguageTable'


@dataclasses.dataclass
class Concept(FieldnamesMixin):
    """Essential data of a concept mapped to Concepticon."""
    ID: Optional[str] = ''  # pylint: disable=C0103
    Name: Optional[str] = ''  # pylint: disable=C0103
    Concepticon_ID: Optional[str] = None  # pylint: disable=C0103
    Concepticon_Gloss: Optional[str] = None  # pylint: disable=C0103

    def __hash__(self):
        return hash(self.ID)

    @classmethod
    def __cldf_table__(cls):
        return 'ParameterTable'


def concepticon_concepts(concept_lists: Iterable[Conceptlist]) -> type:
    """Create a dataclass on the fly for the additional columns in conceptlists."""
    attrib = []
    for cl in concept_lists:
        for col in cl.metadata.tableSchema.columns:
            if col.name not in ['ID', 'CONCEPTICON_ID', 'CONCEPTICON_GLOSS']:
                attrib.append(
                    (col.name, str, dataclasses.field(default=None)))  # pylint: disable=E3701
    return dataclasses.make_dataclass("ConcepticonConcept", attrib, bases=(Concept,))


@dataclasses.dataclass
class Lexeme(FieldnamesMixin):  # pylint: disable=R0902
    """
    Raw lexical data item as it can be pulled out of the original datasets.

    This is the basis for creating rows in CLDF representations of the data by
    - splitting the lexical item into forms
    - cleaning the forms
    - potentially tokenizing the form
    """
    ID: str  # pylint: disable=C0103
    Form: str  # pylint: disable=C0103
    Value: str  # the lexical item  # pylint: disable=C0103
    Language_ID: str  # pylint: disable=C0103
    Parameter_ID: str  # pylint: disable=C0103
    Local_ID: Optional[str] = None  # local ID in the source dataset  # pylint: disable=C0103
    Segments: list[str] = dataclasses.field(default_factory=list)  # pylint: disable=C0103
    Graphemes: Optional[list[str]] = None  # pylint: disable=C0103
    Profile: Optional[str] = None  # key of profile used for segmentation  # pylint: disable=C0103
    Source: list[str] = dataclasses.field(default_factory=list)  # pylint: disable=C0103
    Comment: Optional[str] = None  # pylint: disable=C0103
    Cognacy: Optional[str] = None  # pylint: disable=C0103
    Loan: Optional[bool] = None  # pylint: disable=C0103

    def __post_init__(self):
        try:
            assert self.Value
            assert self.Language_ID
            assert self.Parameter_ID
        except AssertionError as e:
            raise ValueError('Illegal NULL value') from e
        if isinstance(self.Source, str):
            self.Source = [self.Source]  # pragma: no cover

    @classmethod
    def __cldf_table__(cls):
        return 'FormTable'


@dataclasses.dataclass
class Cognate(FieldnamesMixin):  # pylint: disable=R0902
    """A cognate or rather a cognacy judgement."""
    ID: Optional[str] = None  # pylint: disable=C0103
    Form_ID: Optional[str] = None  # pylint: disable=C0103
    Form: Optional[str] = None  # pylint: disable=C0103
    Cognateset_ID: Optional[str] = None  # pylint: disable=C0103
    Doubt: bool = False  # pylint: disable=C0103
    Cognate_Detection_Method: str = 'expert'  # pylint: disable=C0103
    Source: list[str] = dataclasses.field(default_factory=list)  # pylint: disable=C0103
    Alignment: Optional[list[str]] = None  # pylint: disable=C0103
    Alignment_Method: Optional[str] = None  # pylint: disable=C0103
    Alignment_Source: Optional[str] = None  # pylint: disable=C0103

    def __post_init__(self):
        if isinstance(self.Alignment, str):
            self.Alignment = self.Alignment.split()  # pragma: no cover
        if not isinstance(self.Doubt, bool):
            self.Doubt = eval(self.Doubt)  # pragma: no cover  # pylint: disable=W0123
        if isinstance(self.Source, str):
            self.Source = [self.Source]  # pragma: no cover

    @classmethod
    def __cldf_table__(cls):
        return 'CognateTable'
