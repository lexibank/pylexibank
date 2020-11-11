import zipfile
import attr
import json
import re
import collections

from clldutils.misc import slug
from pylexibank import Concept, Language, Lexeme
from pylexibank.dataset import Dataset
from pylexibank.forms import FormSpec
from pylexibank.util import progressbar
from csvw import dsv


@attr.s
class SNDCMPConcept(Concept):
    """
    The corresponding gloss as second language other than English
    has to be declared as subclass of SNDCMPConcept within the study repo.
    Example:

    from pylexibank.providers.sndcmp import SNDCMPConcept
    ...
    @attr.s
    class CustomConcept(SNDCMPConcept):
        Bislama_Gloss = attr.ib(default=None)

    class Dataset(BaseDataset):
        ...
        concept_class = CustomConcept
    """
    # Corresponds to 'IxElicitation-IxMorphologicalInstance'
    # in SndComp table Words_*
    IndexInSource = attr.ib(default=None)


@attr.s
class SNDCMPLanguage(Language):
    LongName = attr.ib(default=None)
    # Corresponds to LanguageIX in SndComp DB Langusages_*
    IndexInSource = attr.ib(default=None)
    IsProto = attr.ib(default=None)


@attr.s
class SNDCMPLexeme(Lexeme):
    # Identifes a lexeme as pronouciation variant of ID
    Variant_Of = attr.ib(default=None)


class SNDCMP(Dataset):
    """
    To use this class it is necessary to declare these class variables
    within the study repo

    Example:
    class Dataset(BaseDataset):
        ...
        study_name = 'Vanuatu'
        second_gloss_lang = 'Bislama'
        source_id_array = ['Shimelman2019']
        create_cognates = False

        # optional:
        form_placeholder = '►' # if one wants to import forms without transcriptions (only audio)
        only_proto_forms = True # if one wants to import forms of 'proto'-languages
                                  (special case for MixeZoque) - only vaid with given
                                  'form_placeholder'
        ...

    If there is no corresponding gloss as second language then set
        ...
        self.second_gloss_lang = None


    In addition two files `languages.csv` and `concepts.csv` are needed in folder `etc`.
    To generate them it's necessary to implement a sub-command within the study repo
    called sndcmp{study_name}.create_ref_etc_files and run it as
    `cldfbench sndcmp{study_name}.create_ref_etc_files ./cldfbench_sndcmp{study_name}.py`.
    The generated files will be found in folder `raw`.
    """

    catalog_file_name = 'catalog.json'

    language_class = SNDCMPLanguage
    lexeme_class = SNDCMPLexeme
    concept_class = SNDCMPConcept

    form_spec = FormSpec(
        brackets={},
        replacements=[],
        separators='',
        missing_data=('..', '--', '**', '-..', '...', '÷'),
        strip_inside_brackets=False,
        normalize_unicode='NFC',
    )

    def __init__(self, concepticon=None, glottolog=None):
        self.data_file_name = '{0}.json'.format(self.study_name.lower())
        self.create_cognates = self.create_cognates
        super().__init__(concepticon=concepticon, glottolog=glottolog)

    # subclass this method for study relevant exceptions
    def get_source_id_array(self, lexeme):
        return self.source_id_array

    def cmd_create_ref_etc_files(self, args):
        # Helper command to generate raw/concepts.csv and raw/languages.csv out of
        # the JSON data file which can be used to detect changes for the files
        # etc/concepts.csv and etc/langauges.csv

        if not hasattr(self, 'second_gloss_lang'):
            self.second_gloss_lang = None

        # Load JSON data
        json_data = self.raw_dir.read_json(self.data_file_name)

        longnames = {rl['LanguageIx']:
                     rl['RegionGpMemberLgNameLongInThisSubFamilyWebsite'].strip()
                     for rl in json_data['regionLanguages']}

        # Create raw/languages.csv for usage as etc/languages.csv
        fname = self.raw_dir / 'languages.csv'
        seen_codes = {}
        with dsv.UnicodeWriter(fname) as f:
            f.writerow(['ID', 'Name', 'LongName', 'Glottocode', 'Glottolog_Name', 'ISO639P3code',
                        'Macroarea', 'Latitude', 'Longitude', 'Family', 'IndexInSource', 'IsProto'])
            for language in sorted(json_data['languages'],
                                   key=lambda k: int(k['LanguageIx'])):

                # Build ID
                lang_id = slug(language['ShortName']).capitalize()

                language['GlottoCode'] = language['GlottoCode'].strip()\
                    if language['GlottoCode'] else ''
                # add to language map
                if language['GlottoCode'] in seen_codes:
                    gldata = seen_codes[language['GlottoCode']]
                else:
                    gldata = args.glottolog.api.languoid(
                        language['GlottoCode'])
                    seen_codes[language['GlottoCode']] = gldata

                isProto = False
                if language['isProtoLanguage'] == '1':
                    isProto = True

                lngName = ''
                if longnames.get(language['LanguageIx'], ''):
                    if longnames[language['LanguageIx']] != language['ShortName'].strip():
                        lngName = longnames[language['LanguageIx']].strip()

                f.writerow([
                    lang_id,
                    language['ShortName'].strip(),
                    lngName,
                    language['GlottoCode'],
                    gldata.name if gldata else '',
                    language['ISOCode'].strip(),
                    gldata.macroareas[0].name if gldata and gldata.macroareas else '',
                    language['Latitude'].strip() if language['Latitude'] else '',
                    language['Longtitude'].strip() if language['Longtitude'] else '',
                    gldata.family.name if gldata and gldata.family else '',
                    language['LanguageIx'].strip(),
                    isProto
                ])

        # Create raw/concepts.csv to compare it against etc/concepts.csv
        fname = self.raw_dir / 'concepts.csv'
        with dsv.UnicodeWriter(fname) as f:
            if self.second_gloss_lang is None:
                f.writerow(['ID', 'Name', 'Concepticon_ID', 'Concepticon_Gloss',
                            'IndexInSource'])
            else:
                f.writerow(['ID', 'Name', 'Concepticon_ID', 'Concepticon_Gloss',
                            '{0}_Gloss'.format(self.second_gloss_lang), 'IndexInSource'])
            for c_idx, concept in enumerate(sorted(json_data['words'],
                                                   key=lambda k: (
                    int(k['IxElicitation']),
                    int(k['IxMorphologicalInstance'])))):
                # Build ID
                concept_id = '%i_%s' % (
                    c_idx + 1, slug(concept['FullRfcModernLg01']))

                # Unmapped concepts are reported with int(ID)<1 in source
                if int(concept['StudyDefaultConcepticonID']) > 0:
                    concepticon_id = concept['StudyDefaultConcepticonID']
                    co_gloss = args.concepticon.api.conceptsets[concepticon_id].gloss
                else:
                    concepticon_id = None
                    co_gloss = ''
                if self.second_gloss_lang is None:
                    f.writerow([
                        concept_id,
                        concept['FullRfcModernLg01'],
                        concepticon_id,
                        co_gloss,
                        '%s-%s' % (concept['IxElicitation'],
                                   concept['IxMorphologicalInstance']),
                    ])
                else:
                    f.writerow([
                        concept_id,
                        concept['FullRfcModernLg01'],
                        concepticon_id,
                        co_gloss,
                        concept['FullRfcModernLg02'],
                        '%s-%s' % (concept['IxElicitation'],
                                   concept['IxMorphologicalInstance']),
                    ])

    def cmd_download(self, args):
        # download raw JSON data from https://soundcomparisons.com into folder /raw
        self.raw_dir.download(
            'https://soundcomparisons.com/query/data?study={0}'.format(self.study_name),
            self.data_file_name)

        # Get all FilePathParts from Languages
        json_data = self.raw_dir.read_json(self.data_file_name)
        language_FilePathParts = [
            lang['FilePathPart'] for lang in json_data['languages']]

        # download raw sound file catalog as JSON data
        with self.raw_dir.temp_download(
                'https://github.com/clld/soundcomparisons-data/'
                'raw/master/soundfiles/catalog.json.zip',
                '_cat_temp.json.zip') as p:
            with zipfile.ZipFile(str(p), 'r') as z:
                for filename in z.namelist():
                    with z.open(filename) as f:
                        json_cat = json.loads(f.read().decode('utf-8'))
                    break

        # Prune catalog to used sound files only
        catalog = {json_cat[oid]['metadata']['name']: dict(**json_cat[oid], id=oid)
                   for oid in json_cat
                   if re.split(r'_\d+_', json_cat[oid]['metadata']['name'])[0]
                   in language_FilePathParts}
        with open(str(self.raw_dir / self.catalog_file_name), 'w', encoding='utf-8') as f:
            json.dump(collections.OrderedDict(sorted(catalog.items())),
                      f, ensure_ascii=False, indent=1)

    def cmd_makecldf(self, args):

        if not hasattr(self, 'form_placeholder'):
            self.form_placeholder = None
        if not hasattr(self, 'only_proto_forms'):  # special case for MixeZoque
            self.only_proto_forms = False

        sound_cat = self.raw_dir.read_json(self.catalog_file_name)

        # add sources
        args.writer.add_sources()

        # add languages from explicit file
        concepts = {}
        for concept in self.concepts:
            args.writer.add_concept(**concept)
            concepts[concept['IndexInSource']] = concept['ID']
        languages = {}
        proto_lgs = []
        for language in self.languages:
            args.writer.add_language(**language)
            languages[language['IndexInSource']] = language['ID']
            if language.get('IsProto', '') == 'True':
                proto_lgs.append(language['IndexInSource'])

        # Load JSON data
        json_data = self.raw_dir.read_json(self.data_file_name)

        # collect missing languages
        missing = set()
        # collect lexemes with no transcription but with audio
        only_snd = []

        media = []
        args.writer.cldf.add_table(
            'media.csv',
            'ID',
            'Description',
            'URL',
            'mimetype',
            {'name': 'size', 'datatype': 'integer'},
            'Form_ID',
            primaryKey=['ID']
        )

        args.writer.cldf.add_foreign_key(
            'media.csv', 'Form_ID', 'FormTable', 'ID', )

        # Add lexemes
        for idx in progressbar(sorted(json_data['transcriptions'], key=lambda k: (
            int(json_data['transcriptions'][k]['LanguageIx']),
            int(json_data['transcriptions'][k]['IxElicitation']),
            int(json_data['transcriptions'][k]['IxMorphologicalInstance'])
        )), desc='makecldf'):
            lexeme = json_data['transcriptions'][idx]

            if lexeme['LanguageIx'] not in languages:  # pragma: no cover
                missing.add(lexeme['LanguageIx'])
                continue

            # If entry is marked as 'isDummy' => it only has audio
            if 'isDummy' in lexeme:
                if self.form_placeholder:
                    if isinstance(lexeme['soundPaths'], list) and isinstance(
                            lexeme['soundPaths'][0], list):
                        lexeme['Phonetic'] = [self.form_placeholder] * len(lexeme['soundPaths'])
                        lexeme['AlternativePhoneticRealisationIx'] = \
                            ['0'] * len(lexeme['soundPaths'])
                        lexeme['WCogID'] = [''] * len(lexeme['soundPaths'])
                    else:
                        lexeme['Phonetic'] = self.form_placeholder
                        lexeme['AlternativePhoneticRealisationIx'] = '0'
                        lexeme['WCogID'] = ''
                lexeme['path'] = lexeme['soundPaths'][0].split('/')[-1].split('.')[0]
                lexeme['AlternativeLexemIx'] = '0'
                lexeme['RootIsLoanWordFromKnownDonor'] = '0'

            # Replace all forms by 'form_placeholder' if language is not a propto language
            # Special case for MixeZoque
            if self.form_placeholder and \
                    self.only_proto_forms and lexeme['LanguageIx'] not in proto_lgs:
                if isinstance(lexeme['Phonetic'], list):
                    lexeme['Phonetic'] = [self.form_placeholder] * len(lexeme['soundPaths'])
                else:
                    if not lexeme['Phonetic'].strip()\
                            or lexeme['Phonetic'].strip() in self.form_spec.missing_data:
                        continue
                    lexeme['Phonetic'] = self.form_placeholder

            if 'Phonetic' not in lexeme:
                if 'isDummy' in lexeme:
                    only_snd.append(lexeme)
                continue

            # If there is only one elictation for a meaning
            # it comes as plain string (otherwise as list).
            # Turn relevant items into a list as well.
            if isinstance(lexeme['Phonetic'], str):
                lexeme['Phonetic'] = [lexeme['Phonetic']]
                lexeme['path'] = [lexeme['path']]
                lexeme['soundPaths'] = [lexeme['soundPaths']]
                lexeme['WCogID'] = [lexeme['WCogID']]

            ref_id = None
            last_altlex = None
            for i, value in enumerate(lexeme['Phonetic']):
                v = value.strip()
                # Skip if value is empty
                if not v or v in self.form_spec.missing_data:
                    continue
                # Commas are not allowed!
                if ',' in v:  # pragma: no cover
                    args.log.warn('Comma not allowed in /{0}/ for {1} - {2}'.format(
                        value, languages[lexeme['LanguageIx']], lexeme['IxElicitation']))
                param_id = concepts['{0}-{1}'.format(
                    lexeme['IxElicitation'], lexeme['IxMorphologicalInstance'])]

                new = args.writer.add_form(
                    Language_ID=languages[lexeme['LanguageIx']],
                    Local_ID='{0}-{1}-{2}'.format(
                        lexeme['LanguageIx'],
                        lexeme['IxElicitation'],
                        lexeme['IxMorphologicalInstance']),
                    Parameter_ID=param_id,
                    Value=v,
                    Form=v,
                    Loan=(lexeme['RootIsLoanWordFromKnownDonor'] == '1'),
                    Source=self.get_source_id_array(lexeme),
                    Variant_Of=ref_id if int(
                        lexeme['AlternativePhoneticRealisationIx'][i]) > 0 else None,
                )

                # add media
                if len(lexeme['soundPaths'][0]) > 0 and len(lexeme['soundPaths'][i][0]) > 0:
                    if lexeme['path'][i] in sound_cat:
                        for bs in sorted(sound_cat[lexeme['path'][i]]['bitstreams'],
                                         key=lambda x: x['content-type']):
                            media.append({
                                'ID': bs['checksum'],
                                'Description': lexeme['path'][i],
                                'URL': 'https://cdstar.shh.mpg.de/bitstreams/{0}/{1}'.format(
                                    sound_cat[lexeme['path'][i]]['id'], bs['bitstreamid']),
                                'mimetype': bs['content-type'],
                                'size': bs['filesize'],
                                'Form_ID': new['ID']
                            })
                    else:  # pragma: no cover
                        args.log.warn('Missing sound file name in catalog {0}.'.format(
                            lexeme['path'][i]))

                # Remember last inserted ID for alternative pronounciations to insert 'Variant_Of'.
                # This can be done in that way since the downloaded json data are sort
                # by altlex and altpron.
                if last_altlex != int(lexeme['AlternativeLexemIx'][i]):
                    ref_id = new['ID']
                last_altlex = int(lexeme['AlternativeLexemIx'][i])

                # add cognate if desired
                if self.create_cognates:
                    wcogid = None
                    if lexeme['WCogID'][i].strip():
                        try:
                            wid = int(lexeme['WCogID'][i])
                            if wid > 0:
                                wcogid = '{0}-{1}'.format(param_id, wid)
                        except ValueError:
                            wcogid = '{0}-{1}'.format(param_id, lexeme['WCogID'][i])
                    if wcogid:
                        args.writer.add_cognate(
                            lexeme=new,
                            Cognateset_ID=wcogid,
                            Source=self.source_id_array,
                        )

        args.writer.write(
            **{'media.csv': media}
        )

        for m in sorted(missing):  # pragma: no cover
            args.log.warn('Missing language with ID {0}.'.format(m))

        if len(only_snd):
            args.log.info('Consider to use "form_placeholder" to import lexemes without '
                          'transcription but with audio:')
        for m in only_snd:  # pragma: no cover
            args.log.warning('Missing transcription for {0}-{1}-{2}.'.format(
                m['LanguageIx'], m['IxElicitation'], m['IxMorphologicalInstance']))
