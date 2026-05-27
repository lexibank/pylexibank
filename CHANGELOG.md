# Changes

The `pylexibank` package adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## 4.0.0 - 2026-05-27

- Removed lexibank db functionality.
- Compatibility with pycldf 2.x

### Backwards incompatibility

Note that Lexibank datasets curated with pylexibank 3.x might not be compatible with pylexibank 4.0.
This will be the case, when datasets define custom object classes derived from `pylexibank.models` classes.
These models used to be defined using the `attrs` package - and so inheriting classes needed to be
`@attr.s`-decorated as well. Now, models are `@dataclasses.dataclass` decorated, and custom models
should be as well. Thus, the typical upgrade will only require swapping out `attrs` functionality for
the corresponding `dataclasses` constructs.

This may look as in the following example `diff`:
```diff
-@attr.s
+@dataclasses.dataclass
 class CustomConcept(pylexibank.Concept):
-    Local_ID = attr.ib(default=None)
-    Spanish_Gloss = attr.ib(default=None)
-    Scientific_Name = attr.ib(default=None)
-    Concepticon_SemanticField = attr.ib(default=None)
+    Local_ID: Optional[str] = None
+    Spanish_Gloss: Optional[str] = None
+    Scientific_Name: Optional[str] = None
+    Concepticon_SemanticField: Optional[str] = None
```


## 3.5.0 - 2024-07-04

- Changed behaviour of makecldf so it does not remove languages or parameters explicitly added by the user.
- Run tests on python 3.8–3.12
