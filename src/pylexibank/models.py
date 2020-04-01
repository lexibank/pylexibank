import attr

__all__ = [
    'Language', 'Lexeme', 'Concept', 'Cognate', 'CONCEPTICON_CONCEPTS', 'concepticon_concepts']

CONCEPTICON_CONCEPTS = 1


def non_empty(_, attribute, value):
    if not value:
        raise ValueError('{0} must be non-empty'.format(attribute))


class FieldnamesMixin(object):
    @classmethod
    def fieldnames(cls):
        return [f.name for f in attr.fields(cls)]


@attr.s(hash=False)
class Language(FieldnamesMixin):
    ID = attr.ib(default='', hash=True)
    Name = attr.ib(default=None)
    ISO639P3code = attr.ib(default=None)
    Glottocode = attr.ib(default=None)
    Macroarea = attr.ib(default=None)
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)

    Glottolog_Name = attr.ib(default=None)
    Family = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'LanguageTable'


@attr.s(hash=False)
class Concept(FieldnamesMixin):
    ID = attr.ib(default='', hash=True)
    Name = attr.ib(default='')
    Concepticon_ID = attr.ib(default=None)
    Concepticon_Gloss = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'ParameterTable'


def concepticon_concepts(concept_lists):
    attrib = {}
    for cl in concept_lists:
        for col in cl.metadata.tableSchema.columns:
            if col.name not in ['ID', 'CONCEPTICON_ID', 'CONCEPTICON_GLOSS']:
                attrib[col.name] = attr.ib(default=None)
    return attr.make_class("ConcepticonConcept", attrib, bases=(Concept,))


@attr.s
class Lexeme(FieldnamesMixin):
    """
    Raw lexical data item as it can be pulled out of the original datasets.

    This is the basis for creating rows in CLDF representations of the data by
    - splitting the lexical item into forms
    - cleaning the forms
    - potentially tokenizing the form
    """
    ID = attr.ib()
    Form = attr.ib()
    Value = attr.ib(validator=non_empty)  # the lexical item
    Language_ID = attr.ib(validator=non_empty)
    Parameter_ID = attr.ib(validator=non_empty)
    Local_ID = attr.ib(default=None)  # local ID of a lexeme in the source dataset
    Segments = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list))
    Graphemes = attr.ib(default=None)
    Profile = attr.ib(default=None)  # key of the profile used to create the segmentation
    Source = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        converter=lambda v: [v] if isinstance(v, str) else v)
    Comment = attr.ib(default=None)
    Cognacy = attr.ib(default=None)
    Loan = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(bool)))

    @classmethod
    def __cldf_table__(cls):
        return 'FormTable'


@attr.s
class Cognate(FieldnamesMixin):
    ID = attr.ib(default=None)
    Form_ID = attr.ib(default=None)
    Form = attr.ib(default=None)
    Cognateset_ID = attr.ib(default=None)
    Doubt = attr.ib(
        default=False,
        converter=lambda v: v if isinstance(v, bool) else eval(v))
    Cognate_Detection_Method = attr.ib(default='expert')
    Source = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        converter=lambda v: [v] if isinstance(v, str) else v)
    Alignment = attr.ib(
        default=None,
        converter=lambda v: v if isinstance(v, list) or v is None else v.split())
    Alignment_Method = attr.ib(default=None)
    Alignment_Source = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'CognateTable'
