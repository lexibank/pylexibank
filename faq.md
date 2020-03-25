# Tackling common issues

## Orthography profiles

Data can be automatically segmented if a dataset provides an orthography profile 
([Moran and Cysouw 2018](https://doi.org/10.5281/zenodo.1296780)). In the simplest
case, this would be a single file `etc/orthography.tsv`, specifying the orthography
of the whole dataset.

Often, though, in particular for aggregated datasets, the orthographies vary
considerably between languages in the dataset. In this case, per-language profiles
can be useful. This can be accomplished by providing a set of profile files
in the **directory** `etc/orthography`, where each profile follows the file name
convention `<Language_ID>.tsv`.

Sometimes, even more flexibility is needed, e.g. when the orthographies used in a
dataset vary per contributor and not per language. In this case, `etc/orthography`
may hold any number of profile files named `<Profile_ID>.tsv`, and the profile
selection **per form** is controlled by passing a keyword argument 
`profile=<Profile_ID>` into calls of `LexibnkWriter.add_lexemes`.
