"""
Run makecldf command of a dataset
"""
import html

from clldutils import jsonlib
from cldfbench.cli_util import with_dataset, get_dataset

from pylexibank.cli_util import add_catalogs, add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalogs(parser, with_clts=True)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--dev', action='store_true', default=False)


def run(args):
    dataset = get_dataset(args)
    dataset.concepticon = args.concepticon.api
    dataset.glottolog = args.glottolog.api
    with_dataset(args, 'makecldf', dataset=dataset)
    if not dataset.cldf_dir.joinpath('sources.bib').exists():
        raise ValueError(
            'The dataset has no sources at {0}'.format(dataset.cldf_dir.joinpath('sources.bib')))
    creators, contributors = dataset.get_creators_and_contributors(strict=False)

    def contrib(d):
        return {k: v for k, v in d.items() if k in {'name', 'affiliation', 'orcid', 'type'}}

    with jsonlib.update_ordered(dataset.dir / '.zenodo.json', indent=4) as md:
        md.update(
            {
                "title": dataset.metadata.title,
                "access_right": "open",
                "keywords": sorted(set(md.get("keywords", []) + ["linguistics", "cldf:Wordlist"])),
                "creators": [contrib(p) for p in creators],
                "contributors": [contrib(p) for p in contributors],
                "communities": [
                    {"identifier": community_id}
                    for community_id in sorted(
                        set([r["identifier"] for r in md.get("communities", [])] + ["lexibank"])
                    )
                ],
                "upload_type": "dataset",
            }
        )
        if dataset.metadata.citation:
            md['description'] = "<p>Cite the source of the dataset as:</p>\n\n" \
                                "<blockquote>\n<p>{}</p>\n</blockquote>".format(
                html.escape(dataset.metadata.citation))
        if dataset.metadata.zenodo_license:
            md['license'] = {'id': dataset.metadata.zenodo_license}
