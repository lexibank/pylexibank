import dataclasses
from typing import Optional

__all__ = [
    'Language', 'Lexeme', 'Concept', 'Cognate', 'CONCEPTICON_CONCEPTS', 'concepticon_concepts']

CONCEPTICON_CONCEPTS = 1


class FieldnamesMixin:
    @classmethod
    def fieldnames(cls):
        return [f.name for f in dataclasses.fields(cls)]


@dataclasses.dataclass
class Language(FieldnamesMixin):
    ID: str = ''
    Name: Optional[str] = None
    ISO639P3code: Optional[str] = None
    Glottocode: Optional[str] = None
    Macroarea: Optional[str] = None
    Latitude: Optional[float] = None
    Longitude: Optional[float] = None
    Glottolog_Name: Optional[str] = None
    Family: Optional[str] = None

    def __hash__(self):
        return hash(self.ID)

    @classmethod
    def __cldf_table__(cls):
        return 'LanguageTable'


@dataclasses.dataclass
class Concept(FieldnamesMixin):
    ID: Optional[str] = ''
    Name: Optional[str] = ''
    Concepticon_ID: Optional[str] = None
    Concepticon_Gloss: Optional[str] = None

    def __hash__(self):
        return hash(self.ID)

    @classmethod
    def __cldf_table__(cls):
        return 'ParameterTable'


def concepticon_concepts(concept_lists):
    attrib = []
    for cl in concept_lists:
        for col in cl.metadata.tableSchema.columns:
            if col.name not in ['ID', 'CONCEPTICON_ID', 'CONCEPTICON_GLOSS']:
                attrib.append((col.name, str, dataclasses.field(default=None)))
    return dataclasses.make_dataclass("ConcepticonConcept", attrib, bases=(Concept,))


@dataclasses.dataclass
class Lexeme(FieldnamesMixin):
    """
    Raw lexical data item as it can be pulled out of the original datasets.

    This is the basis for creating rows in CLDF representations of the data by
    - splitting the lexical item into forms
    - cleaning the forms
    - potentially tokenizing the form
    """
    ID: str
    Form: str
    Value: str  # the lexical item
    Language_ID: str
    Parameter_ID: str
    Local_ID: Optional[str] = None  # local ID of a lexeme in the source dataset
    Segments: list[str] = dataclasses.field(default_factory=list)
    Graphemes: Optional[list[str]] = None
    Profile: Optional[str] = None  # key of the profile used to create the segmentation
    Source: list[str] = dataclasses.field(default_factory=list)
    Comment: Optional[str] = None
    Cognacy: Optional[str] = None
    Loan: Optional[bool] = None

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
class Cognate(FieldnamesMixin):
    ID: Optional[str] = None
    Form_ID: Optional[str] = None
    Form: Optional[str] = None
    Cognateset_ID: Optional[str] = None
    Doubt: bool = False
    Cognate_Detection_Method: str = 'expert'
    Source: list[str] = dataclasses.field(default_factory=list)
    Alignment: Optional[list[str]] = None
    Alignment_Method: Optional[str] = None
    Alignment_Source: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.Alignment, str):
            self.Alignment = self.Alignment.split()  # pragma: no cover
        if not isinstance(self.Doubt, bool):
            self.Doubt = eval(self.Doubt)  # pragma: no cover
        if isinstance(self.Source, str):
            self.Source = [self.Source]  # pragma: no cover

    @classmethod
    def __cldf_table__(cls):
        return 'CognateTable'
