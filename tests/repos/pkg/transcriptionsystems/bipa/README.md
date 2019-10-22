# Broad IPA system (BIPA)

This is an attempt to provide a generally broad account on interpreting phonetic symbols as IPA strings. By broad, we mean that we accept many non-standard spelling variants which are not defined in the IPA standard but are nevertheless employed by many users. What we do not offer is an interpretation of ambiguous cases, so if you use `[`c`]` but actually mean `[`ts`]`, our system will still interpret this sound as a "voiceless palatal plosive consonant":

```python
>>> from pyclts.clts import CLTS
>>> clts = CLTS()
>>> print(clts.get_sound('c').name)
voiceless palatal plosive consonant
```
