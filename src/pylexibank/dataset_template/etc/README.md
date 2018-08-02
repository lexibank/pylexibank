# Configuration directory

This directory contains "configuration" data, i.e. data which helps with and
guides the conversion of the raw data to CLDF. Recognized files in this directory
are

- `orthography.tsv`: An orthography profile which will be used for segmentation of
  the forms.
- `concepts.csv`: 
- `languages.csv`:
- `lexemes.csv`: A mapping from "bad" lexemes to better replacements. This is meant
  basically as a list of errata, which are consulted (and fixed) when creating the
  CLDF dataset.
