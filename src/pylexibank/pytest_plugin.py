import pytest
from goodtables import validate
from pycldf import Wordlist


@pytest.fixture
def cldf_dataset():
    return Wordlist.from_metadata('cldf')


@pytest.fixture
def forms_schema():
    return  {
        "fields": [
            {
                "name": "ID",
                "constraints": {
                    "unique": True,
                    "required": True
                }
            },
            {
                "name": "Local_ID",
            },
            {
                "name": "Language_ID",
            },
            {
                "name": "Parameter_ID",
            },
            {
                "name": "Value",
                "constraints": {
                    "required": True
                }
            },
            {
                "name": "Form",
                "constraints": {
                    "required": True
                }
            }
        ]
    }


@pytest.fixture
def forms_report(forms_schema):
    return validate('cldf/forms.csv', schema=forms_schema, row_limit=1000000, infer_fields=True)

