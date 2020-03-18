import pytest
import attr
import zipfile
import io

from csvw.dsv import reader
from clldutils.path import copytree
from pylexibank.providers.sndcmp import SNDCMP
from pylexibank.providers.sndcmp import SNDCMPConcept


JSONSTR = '{"languages":[{"FilePathPart": "Br_Tup_MaAwTG_Aweti_Aweti_Saitao_Dl"}]}'
JSONZIP = '{"EAEA0-4DE0-B3E9-31CE-0":{"metadata":'\
          '{"name":"Br_Tup_MaAwTG_Aweti_Aweti_Saitao_Dl_001_um_one"}}}'


@pytest.fixture
def sndcmp_dataset(repos, tmpdir, glottolog, concepticon):

    copytree(repos / 'datasets' / 'sndcmp', str(tmpdir.join('sndcmp')))

    class CustomConcept(SNDCMPConcept):
        Bislama_Gloss = attr.ib(default=None)

    class Dataset(SNDCMP):
        dir = str(tmpdir.join('sndcmp'))
        id = "sndcmpvanuatu"
        study_name = "Vanuatu"
        second_gloss_lang = "Bislama"
        source_id_array = ["Shimelman2019"]
        create_cognates = True
        concept_class = CustomConcept

    return Dataset()


@pytest.fixture
def sndcmp_dl_dataset(repos, tmpdir, glottolog, concepticon):

    copytree(repos / 'datasets' / 'sndcmp', str(tmpdir.join('sndcmp')))

    class Dataset(SNDCMP):
        dir = str(tmpdir.join('sndcmp'))
        id = "sndcmpbrazil"
        study_name = "Brazil"
        second_gloss_lang = None
        source_id_array = ["xy"]
        create_cognates = False

    return Dataset()


def test_sndcmp(sndcmp_dataset, mocker):

    sndcmp_dataset.cmd_create_ref_etc_files(mocker.MagicMock())
    assert (sndcmp_dataset.raw_dir / 'languages.csv').exists()
    assert (sndcmp_dataset.raw_dir / 'concepts.csv').exists()
    csv = sndcmp_dataset.raw_dir / 'concepts.csv'
    res = list(reader(csv, dicts=True))
    assert len(res) == 3
    assert 'Bislama_Gloss' in res[0]
    assert res[0]["IndexInSource"] == '1-0'


def test_sndcmp_dl(sndcmp_dl_dataset, mocker):

    class Requests(mocker.Mock):
        def get(self, *args, **kw):
            if 'zip' in args[0]:
                s = io.BytesIO()
                z = zipfile.ZipFile(s, 'w')
                z.writestr('catalog.json', JSONZIP.encode('utf8'))
                z.close()
                return mocker.Mock(
                    status_code=200,
                    iter_content=mocker.Mock(return_value=[s.getvalue()]))
            else:
                return mocker.Mock(
                    status_code=200,
                    iter_content=mocker.Mock(return_value=[JSONSTR.encode('utf8')]))

    mocker.patch('cldfbench.datadir.requests', Requests())

    sndcmp_dl_dataset.cmd_download(mocker.Mock())
    assert (sndcmp_dl_dataset.raw_dir / 'brazil.json').exists()
