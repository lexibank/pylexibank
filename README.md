# pylexibank

[![Build Status](https://travis-ci.org/lexibank/pylexibank.png)](https://travis-ci.org/lexibank/pylexibank)
[![codecov](https://codecov.io/gh/lexibank/pylexibank/branch/master/graph/badge.svg)](https://codecov.io/gh/lexibank/pylexibank)
[![PyPI](https://img.shields.io/pypi/v/pylexibank.svg)](https://pypi.org/project/pylexibank)


## Install

Since `pylexibank` has quite a few dependencies, installing it will result in installing
many other python packages along with it. To avoid any side effects for your default
python installation, we recommend installation in a
[virtual environment](https://virtualenv.pypa.io/en/stable/).

Some code of `pylexibank` relies on LingPy functionality which is not yet released, thus,
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
way to achieve this is by cloning [clld/glottolog](https://github.com/clld/glottolog) and
[clld/concepticon-data](https://github.com/clld/concepticon-data). But you could also download
(and unpack) a released version of these repositories.


## Usage

`pylexibank` can be used in two ways:
- The command line interface provides mainly access to the functionality for the `lexibank`
  curation workflow.
- The `pylexibank` package can also be used like any other python package in your own
  python code to access lexibank data in a programmatic (and consistent) way.

