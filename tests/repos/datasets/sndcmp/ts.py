import pathlib
import attr

from pylexibank.providers.sndcmp import SNDCMP
from pylexibank.providers.sndcmp import SNDCMPConcept

@attr.s
class TestConcept(SNDCMPConcept):
    Bislama_Gloss = attr.ib(default=None)


class Test(SNDCMP):
    dir = pathlib.Path(__file__).parent
    id = "testsndcmp"

    study_name = "Vanuatu"
    second_gloss_lang = "Bislama"
    source_id_array = ["Shimelman2019"]
    create_cognates = True

    concept_class = TestConcept

