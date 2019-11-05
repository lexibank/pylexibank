# pylexibank

[![Build Status](https://travis-ci.org/lexibank/pylexibank.png)](https://travis-ci.org/lexibank/pylexibank)
[![codecov](https://codecov.io/gh/lexibank/pylexibank/branch/master/graph/badge.svg)](https://codecov.io/gh/lexibank/pylexibank)
[![PyPI](https://img.shields.io/pypi/v/pylexibank.svg)](https://pypi.org/project/pylexibank)

`pylexibank` is a python package providing functionality to curate and aggregate
[Lexibank](https://github.com/lexibank/lexibank) datasets.


## Install

Since `pylexibank` has quite a few dependencies, installing it will result in installing
many other python packages along with it. To avoid any side effects for your default
python installation, we recommend installation in a
[virtual environment](https://virtualenv.pypa.io/en/stable/).

Now you may install `pylexibank` via pip or in development mode following the instructions
in [CONTRIBUTING.md](CONTRIBUTING.md).

Installing `pylexibank` will also install [`cldfbench`](https://github.com/cldf/cldfbench), which in turn installs a cli command `cldfbench`. This command is used
to run `pylexibank` functionality from the command line as subcommands.

`cldfbench` is also used to [manage reference catalogs](https://github.com/cldf/cldfbench/#catalogs), in particular Glottolog,
Concepticon and CLTS. Thus, after installing `pylexibank` you should run
```shell script
cldfbench catconfig
```
to make sure the catalog data is locally available and `pylexibank` knows about it.


## Usage

`pylexibank` can be used in two ways:
- The command line interface provides mainly access to the functionality for the `lexibank`
  curation workflow.
- The `pylexibank` package can also be used like any other python package in your own
  python code to access lexibank data in a programmatic (and consistent) way.


### The `cmd_makecldf` method

The main goal of `pylexibank` is creating high-quality CLDF Wordlists. This
happens in the custom `cmd_makecldf` method of a Lexibank dataset. To make this task
easier, `pylexibank` provides
- **access to Glottolog and Concepticon data:**
  - `args.glottolog.api` points to an instance of [`CachingGlottologAPI`](https://github.com/cldf/cldfbench/blob/f373855e3b9cde029578e77c26136f0df26a82fa/src/cldfbench/catalogs.py#L10-L40) (a subclass of `pyglottolog.Glottolog`)
  - `args.concepticon.api` points to an instance of [`CachingConcepticonAPI`](https://github.com/cldf/cldfbench/blob/f373855e3b9cde029578e77c26136f0df26a82fa/src/cldfbench/catalogs.py#L48-L51) (a subclass of `pyconcepticon.Concepticon`)
- **fine-grained control over form manipulation** via a `Dataset.form_spec`, an instance
  of [`pylexibank.FormSpec`](src/pylexibank/forms.py) which can be customized per
  dataset. `FormSpec` is meant to capture the rules that have been used when compiling
  the source data - for cases where the source data violates these rules, wholesale
  replacement by listing a lexeme in `etc/lexemes.csv` is recommended.
- **support for additional information** on lexemes, cognates, concepts and languages via
  subclassing the defaults in [`pylexibank.models`](src/pylexibank/models.py)
- **easy access to configuration data** in a dataset's `etc_dir`
- **support for segmentation** using the [`segments`](https:pypi.org/project/segments)
  package with orthography profile(s):
  - If an orthography profile is available as `etc/orthography.tsv`, a `segments.Tokenizer`
    instance, initialized with this profile, will be available as `Dataset.tokenizer`
    and automatically used by `LexibankWriter.add_form`.
  - If a directory `etc/orthography/` exists, all `*.tsv` files in it will be considered
    orthography profiles, and a `dict` mapping filename stem to tokenizer will be available. Tokenizer
    selection can be controlled in two ways:
    - Passing a keyword `profile=FILENAME_STEM` in `Dataset.tokenizer()` calls.
    - Provide orthography profiles for each language and let `Dataset.tokenizer`
      chose the tokenizer by `item['Language_ID']`.


## Programmatic access to Lexibank datasets

While some level of support for reading and writing any [CLDF](https://cldf.clld.org) dataset is already provided by the [`pycldf` package](https://pypi.org/projects/pycldf), `pylexibank` (building on `cldfbench`) adds another layer of abstraction which supports 
- treating Lexibank datasets as Python packages (and managing them via `pip`),
- a multi-step curation workflow
- aggregating collections of Lexibank datasets into a single SQLite database for efficient analysis.


### Installable and `pylexibank` enabled datasets

Turning a Lexibank dataset into a (`pip` installable) Python package is as simple as writing a [setup script](https://docs.python.org/3/distutils/setupscript.html) `setup.py`.
But to make the dataset available for curation via `pylexibank`, the dataset must provide 
- a python module 
- containing a class derived from `pylexibank.Dataset`, which specifies
  - `Dataset.dir`: A directory relative to which the the [curation directories](dataset.md) are located.
  - `Dataset.id`: An identifier of the dataset.
- which is advertised as `lexibank.dataset` [entry point](https://packaging.python.org/specifications/entry-points/) in `setup.py`. E.g.
  ```python
      entry_points={
          'lexibank.dataset': [
              'sohartmannchin=lexibank_sohartmannchin:Dataset',
          ]
      },
  ```

Turning datasets into `pylexibank` enabled python packages has multiple advantages:
- Datasets can be installed from various sources, e.g. GitHub repositories.
- Requirements files can be used "pin" particular versions of datasets for installation.
- Upon installation datasets can be discovered programmatically.
- [Virtual environments](https://virtualenv.pypa.io/en/latest/) can be used to manage projects which require different versions of the same dataset.


#### Conventions

1. Dataset identifier should be lowercase and either:
   - the database name, if this name is established and well-known (e.g. "abvd", "asjp" etc),
   - \<author\>\<languagegroup\> (e.g. "grollemundbantu" etc)
2. Datasets that require preprocessing with external programs (e.g. antiword, libreoffice) should store intermediate/artifacts in ./raw/ directory, and the `cmd_install` code should install from that rather than requiring an external dependency.
3. Declaring a dataset's dependence on `pylexibank`:
   - specify minimum versions in `setup.py`, i.e. require `pylexibank>=1.x.y`
   - specify exact versions in dataset's `cldf-metadata.json` using `prov:createdBy` property (`pylexibank` will take care of this when the CLDF is created via `lexibank makecldf`).


#### Datasets on GitHub

GitHub provides a very good platform for collaborative curation of textual data
such as Lexibank datasets.

Dataset curators are encouraged to make use of features in addition to the just version control, such as
- releases
- README.md, LICENSE, CONTRIBUTORS.md

Note that for datasets curated with `pylexibank`, summary statistics will be written to `README.md` as part of the `makecldf` command.

In addition to the support for collaboratively editing and versioning data, GitHub supports tying into additional services via webhooks. In particular, two of these services are relevant for Lexibank datasets:

- Continuous integration, e.g. via Travis-CI
- Archiving with Zenodo. Notes:
  - When datasets are curated on GitHub and hooked up to ZENODO to trigger automatic deposits of releases, the release tag **must** start with a letter (otherwise the deposit will fail).
  - Additional tags can be added to add context - e.g. when a release is triggered by a specific use case (for example the CLICS 2.0 release). This can be done using `git` as follows:
    ```bash
    git checkout tags/vX.Y.Z
    git tag -a "clics-2.0"
    git push origin --tags
    ```


### Attribution

There are multiple levels of contributions to a Lexibank dataset:
- Typically, Lexibank datasets are derived from published data (be it supplemental material of a paper or public databases). Attribution to this source dataset is given by specifying its full citation in the dataset's metadata and by adding the source title to the release title of a lexibank dataset.
- Often the source dataset is also an aggregation of data from other sources. If possible, these sources (and the corresponding references) are kept in the Lexibank dataset's CLDF; otherwise we refer to the source dataset for a description of its sources.
- Deriving a Lexibank dataset from a source dataset using the `pylexibank` curation workflow involves adding code, mapping to reference catalogs and to some extent also linguistic judgements. These contributions are listed in a dataset's `CONTRIBUTORS.md` and translate to the list of authors of released versions of the lexibank dataset.
