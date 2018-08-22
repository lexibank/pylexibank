# coding: utf-8
from __future__ import unicode_literals


def test_valid(cldf_dataset, cldf_logger):
    assert cldf_dataset.validate(log=cldf_logger)
