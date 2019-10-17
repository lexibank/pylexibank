import attr
from lingpy import Wordlist

from pylexibank import lingpy_util
from pylexibank import models as pbds


def test_wordlist2cognates(repos, mocker, dataset):
    @attr.s
    class Lexeme(pbds.Lexeme):
        Concept = attr.ib(default=None)
        Segments = attr.ib(default=[])
    @attr.s
    class Lexeme2(pbds.Lexeme):
        Concept = attr.ib(default=None)

    dsdir = repos / 'datasets' / 'test_dataset'
    if not dsdir.joinpath('cldf').exists():
        dsdir.joinpath('cldf').mkdir()
    dataset.cognate_class = pbds.Cognate
    dataset.language_class = pbds.Language
    dataset.concept_class = pbds.Concept
    dataset.split_forms = lambda _, s: [s]
    dataset.dir = dsdir
    dataset.tr_analyses = {}
    dataset.cldf_dir = dsdir.joinpath('cldf')

    dataset.lexeme_class = Lexeme
    with dataset.cldf_writer(mocker.Mock()) as ds:
        # needs to be fixed XXX
        ds.tokenize = lambda _, x: []
        ds.add_forms_from_value(
            Value='form,form2',
            Concept='meaning',
            Language_ID='1',
            Parameter_ID='p'
        )

    dataset.lexeme_class = Lexeme2
    with dataset.cldf_writer(mocker.Mock()) as ds2:
        ds2.add_form_with_segments(
            Value='form,form2',
            Concept='meaning',
            Language_ID='1',
            Parameter_ID='p',
            Form='form',
            Segments=['f', 'o']
        )
        # needs to be fixed XXX
        ds2.tokenize = lambda _, x: [x]
        ds2.add_form(
            Value='form,form2',
            Concept='meaning',
            Language_ID='1',
            Parameter_ID='p',
            Form='form',
        )
    # lid, ipa, concept
    wl = Wordlist(lingpy_util._cldf2wld(ds2), row='concept', col='language_id')
    res = list(lingpy_util.wordlist2cognates(wl, 'src'))
    assert isinstance(res[0], dict)
