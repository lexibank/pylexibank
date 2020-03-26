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
`profile=<Profile_ID>` into calls of `LexibankWriter.add_lexemes`.


### Preparing initial orthography profiles with LingPy

In order to prepare an initial orthography profile from your data, you can use the `profile` command 
of `lingpy`, which will be installed along with `pylexibank`. To do so, we assume that you have
already created a first cldf-version of your dataset, with `Value` and `Form` columns
in the `FormTable`. In this case, creating an orthography profile is as easy as typing:

```shell script
$ lingpy profile --clts --cldf --column=form --context -i cldf/cldf-metadata.json -o etc/orthography.tsv
```

This profile will try to normalize your data following the [CLTS](https://clts.clld.org) system, it assumes that data is provided in CLDF format, it takes entries in the column `form`, and also distinguishes three different contexts in which graphemes may occur, namely the beginning of a word, marked by `^`, the end, marked by `$`, and the rest. 


### Caveats in the creation of orthography profiles with context

When correcting such a profile, you have to be careful to remind yourself of the greediness of the orthography profile algorithm provided by the `segments` package. 

If you have a minimal profile like the following one, the profile will fail in parsing the string `n̥ak`, when passed as a form in `lexibank`.

```
Graphemes	IPA
^	NULL
$	NULL
^n	n
n	n
a	a
k$	k
n̥	n̥
```
The reason is that `lexibank` first converts the string into its context representation `^n̥ak$`. It will then search
for the longest subsequence in the beginning of the sequence, where it finds `^n`. This will then be used as a first match, leaving the diacritic `◌̥` unmapped. 
Keep this in mind as it can otherwise seem very surprising, as if the profile would not correctly work.


### Testing orthography profiles interactively with SegmentsJS

In order to test your profile interactively, you can check the interactive implementation of orthography profiles as they are provided in the [SegmentsJS](http://digling.org/calc/profile/) application. You can directly test the behavior by pasting above profile into the application and then pasting the word ``^n̥ak$``. Remember that you should always add the context markers when checking a given sequence that may be wrongly or surprisingly parsed in your lexibank dataset.
