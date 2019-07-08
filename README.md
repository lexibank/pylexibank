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

Some code of `pylexibank` relies on [LingPy](http://lingpy.org/) functionality which is not yet released, thus,
LingPy should be installed from the source repository, running
```
$ git clone https://github.com/lingpy/lingpy/
$ cd lingpy
$ python setup.py install
```

Now you may install `pylexibank` via pip or in development mode following the instructions
in [CONTRIBUTING.md](CONTRIBUTING.md).

Some functionality in `pylexibank` (in particular the `makecldf` sub-command), require access
to [Glottolog](http://glottolog.org) or [Concepticon](http://concepticon.clld.org) data.
Since the data of both these applications is curated in git repositories as well, the easiest
way to achieve this is by cloning [glottolog/glottolog](https://github.com/glottolog/glottolog) and
[concepticon/concepticon-data](https://github.com/concepticon/concepticon-data). But you could also download
(and unpack) a released version of these repositories.


## Usage

`pylexibank` can be used in two ways:
- The command line interface provides mainly access to the functionality for the `lexibank`
  curation workflow.
- The `pylexibank` package can also be used like any other python package in your own
  python code to access lexibank data in a programmatic (and consistent) way.


## Programmatic access to Lexibank datasets

While some level of support for reading and writing any [CLDF](https://cldf.clld.org) dataset is already provided by the [`pycldf` package](https://pypi.org/projects/pycldf), `pylexibank` adds another layer of abstraction which supports 
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

- versioning and releasing
- README.md, LICENSE, CONTRIBUTORS.md

In addition to the support for collaboratively editing and versioning data, GitHub supports tying into additional services via webhooks. In particular, two of these services are relevant for Lexibank datasets:

- Continuous integration, e.g. via Travis-CI
- Archiving with Zenodo
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

