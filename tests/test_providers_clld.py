from pylexibank.providers.clld import CLLD


def test_CLLD(mocker, repos, tmp_path):
    class Response(mocker.Mock):
        def iter_content(self, *args, **kw):
            print(repos.joinpath('wold_dataset.cldf.zip'))
            yield repos.joinpath('wold_dataset.cldf.zip').read_bytes()
    mocker.patch('cldfbench.datadir.get_url', mocker.Mock(return_value=Response()))

    class WOLD(CLLD):
        id = 'wold'
        dir = tmp_path

    ds = WOLD()
    assert ds.url()
    ds._cmd_download(mocker.Mock())
    assert ds.raw_dir.exists()
    assert ds.raw_dir.glob('*.csv')
    assert ds.original_cldf
    with ds.cldf_writer(mocker.Mock()) as w:
        ds.add_sources(w)
