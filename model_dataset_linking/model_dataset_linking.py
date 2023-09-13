# -*- coding: utf-8 -*-

DATASET_TEMPLATE="""\
The information below describes a feature in a dataset with epidemiology data.

Here is some information on the entire dataset:  
dataset name: {obj_name}
dataset description: {obj_description}
                                     
Here is some information on the feature itself:
feature name: {column_name}
feature description: {column_description}
data_type: {column_data_type}
feature unit type: {column_units}
feature numerical stats:  {column_column_stats}
feature concept : {column_concept}
"""
# add to model template
MODEL_TEMPLATE="""\
The information below describes a feature in a epidemiological model.

Here is some information on the entire model:  
model name: {obj_name}
model description: {obj_description}                                  
"""

GROUND_CHUNK_TEMPLATE="""\
name: {ground_name}
description: {ground_description}
synonyms: {ground_synonyms}
"""
# context: {ground_context}
# units: {ground_unit_title}, {ground_units_description}
# type: {ground_type}
# """

from typing import Dict, List
from langchain.vectorstores import Chroma
from langchain.vectorstores.chroma import _results_to_docs_and_scores
from langchain.docstore.document import Document
from langchain.utils import xor_args
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
)
DEFAULT_K = 4 


# to do: add api format to functions for live demo by end of week
# to do: add evaluation data/script
# to do: add other retrieval options (like dkg hops)
# use model type in description?
# to do: try different embedders or similarity search params (is another embedder better at passage level embedding)
# to do: parallelize
# to do: test on dummy data - need better data.. or need to understand models better, time to start getting eval dataset..
# to do: use data cards or other MIT apis or at least use for eval generation?



example_model_description= {"id": "biomd0000000249-model-id",
    "timestamp": "2023-06-12T23:25:26",
    "header": {
      "name": "BIOMD0000000249",
      "description": "BioModels model BIOMD0000000249 processed using MIRA.",
      "schema": "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/petrinet_v0.5/petrinet/petrinet_schema.json",
      "schema_name": "petrinet",
      "model_version": "1.0"
    },
    "username": "Adam Smith"
  }

example_model_get={
  "id": "biomd0000000249-model-id",
  "username": "Adam Smith",
  "timestamp": "2023-06-12 23:25:26",
  "properties": {},
  "model": {
    "states": [
      {
        "id": "N",
        "name": "N",
        "grounding": {
          "identifiers": {
            "ncbitaxon": "9606"
          },
          "modifiers": {}
        }
      },
      {
        "id": "S",
        "name": "S",
        "grounding": {
          "identifiers": {
            "ncbitaxon": "9606"
          },
          "modifiers": {}
        }
      },
      {
        "id": "I_1",
        "name": "I_1",
        "grounding": {
          "identifiers": {},
          "modifiers": {}
        }
      },
      {
        "id": "I_2",
        "name": "I_2",
        "grounding": {
          "identifiers": {},
          "modifiers": {}
        }
      },
      {
        "id": "R_1",
        "name": "R_1",
        "grounding": {
          "identifiers": {
            "ncbitaxon": "9606"
          },
          "modifiers": {}
        }
      },
      {
        "id": "R_2",
        "name": "R_2",
        "grounding": {
          "identifiers": {
            "ncbitaxon": "9606"
          },
          "modifiers": {}
        }
      },
      {
        "id": "I_1p",
        "name": "I_1p",
        "grounding": {
          "identifiers": {},
          "modifiers": {}
        }
      },
      {
        "id": "I_2p",
        "name": "I_2p",
        "grounding": {
          "identifiers": {},
          "modifiers": {}
        }
      },
      {
        "id": "R_p",
        "name": "R_p",
        "grounding": {
          "identifiers": {
            "ncbitaxon": "9606"
          },
          "modifiers": {}
        }
      }
    ],
    "transitions": [
      {
        "id": "t1",
        "input": [
          "N"
        ],
        "output": [
          "N",
          "S"
        ],
        "properties": {
          "name": "t1"
        }
      },
      {
        "id": "t2",
        "input": [
          "S"
        ],
        "output": [],
        "properties": {
          "name": "t2"
        }
      },
      {
        "id": "t3",
        "input": [
          "I_1"
        ],
        "output": [],
        "properties": {
          "name": "t3"
        }
      },
      {
        "id": "t4",
        "input": [
          "I_2"
        ],
        "output": [],
        "properties": {
          "name": "t4"
        }
      },
      {
        "id": "t5",
        "input": [
          "R_1"
        ],
        "output": [],
        "properties": {
          "name": "t5"
        }
      },
      {
        "id": "t6",
        "input": [
          "R_2"
        ],
        "output": [],
        "properties": {
          "name": "t6"
        }
      },
      {
        "id": "t7",
        "input": [
          "I_1p"
        ],
        "output": [],
        "properties": {
          "name": "t7"
        }
      },
      {
        "id": "t8",
        "input": [
          "I_2p"
        ],
        "output": [],
        "properties": {
          "name": "t8"
        }
      },
      {
        "id": "t9",
        "input": [
          "R_p"
        ],
        "output": [],
        "properties": {
          "name": "t9"
        }
      },
      {
        "id": "t10",
        "input": [
          "I_1",
          "S"
        ],
        "output": [
          "I_1",
          "I_1"
        ],
        "properties": {
          "name": "t10"
        }
      },
      {
        "id": "t11",
        "input": [
          "I_1p",
          "S"
        ],
        "output": [
          "I_1p",
          "I_1"
        ],
        "properties": {
          "name": "t11"
        }
      },
      {
        "id": "t12",
        "input": [
          "I_2",
          "S"
        ],
        "output": [
          "I_2",
          "I_2"
        ],
        "properties": {
          "name": "t12"
        }
      },
      {
        "id": "t13",
        "input": [
          "I_2p",
          "S"
        ],
        "output": [
          "I_2p",
          "I_2"
        ],
        "properties": {
          "name": "t13"
        }
      },
      {
        "id": "t14",
        "input": [
          "I_1",
          "R_2"
        ],
        "output": [
          "I_1",
          "I_1p"
        ],
        "properties": {
          "name": "t14"
        }
      },
      {
        "id": "t15",
        "input": [
          "I_1p",
          "R_2"
        ],
        "output": [
          "I_1p",
          "I_1p"
        ],
        "properties": {
          "name": "t15"
        }
      },
      {
        "id": "t16",
        "input": [
          "I_2",
          "R_1"
        ],
        "output": [
          "I_2",
          "I_2p"
        ],
        "properties": {
          "name": "t16"
        }
      },
      {
        "id": "t17",
        "input": [
          "I_2p",
          "R_1"
        ],
        "output": [
          "I_2p",
          "I_2p"
        ],
        "properties": {
          "name": "t17"
        }
      },
      {
        "id": "t18",
        "input": [
          "I_1"
        ],
        "output": [
          "R_1"
        ],
        "properties": {
          "name": "t18"
        }
      },
      {
        "id": "t19",
        "input": [
          "I_2"
        ],
        "output": [
          "R_2"
        ],
        "properties": {
          "name": "t19"
        }
      },
      {
        "id": "t20",
        "input": [
          "I_1p"
        ],
        "output": [
          "R_p"
        ],
        "properties": {
          "name": "t20"
        }
      },
      {
        "id": "t21",
        "input": [
          "I_2p"
        ],
        "output": [
          "R_p"
        ],
        "properties": {
          "name": "t21"
        }
      },
      {
        "id": "t22",
        "input": [
          "R_1"
        ],
        "output": [
          "S"
        ],
        "properties": {
          "name": "t22"
        }
      },
      {
        "id": "t23",
        "input": [
          "R_2"
        ],
        "output": [
          "S"
        ],
        "properties": {
          "name": "t23"
        }
      },
      {
        "id": "t24",
        "input": [
          "R_p"
        ],
        "output": [
          "S"
        ],
        "properties": {
          "name": "t24"
        }
      }
    ]
  },
  "semantics": {
    "ode": {
      "rates": [
        {
          "target": "t1",
          "expression": "N/l_e",
          "expression_mathml": "<apply><divide/><ci>N</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t2",
          "expression": "S/l_e",
          "expression_mathml": "<apply><divide/><ci>S</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t3",
          "expression": "I_1/l_e",
          "expression_mathml": "<apply><divide/><ci>I_1</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t4",
          "expression": "I_2/l_e",
          "expression_mathml": "<apply><divide/><ci>I_2</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t5",
          "expression": "R_1/l_e",
          "expression_mathml": "<apply><divide/><ci>R_1</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t6",
          "expression": "R_2/l_e",
          "expression_mathml": "<apply><divide/><ci>R_2</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t7",
          "expression": "I_1p/l_e",
          "expression_mathml": "<apply><divide/><ci>I_1p</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t8",
          "expression": "I_2p/l_e",
          "expression_mathml": "<apply><divide/><ci>I_2p</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t9",
          "expression": "R_p/l_e",
          "expression_mathml": "<apply><divide/><ci>R_p</ci><ci>l_e</ci></apply>"
        },
        {
          "target": "t10",
          "expression": "365.0*I_1*R0_1*S/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_1</ci><ci>R0_1</ci><ci>S</ci></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t11",
          "expression": "365.0*I_1p*R0_1*S/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_1p</ci><ci>R0_1</ci><ci>S</ci></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t12",
          "expression": "365.0*I_2*R0_2*S/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_2</ci><ci>R0_2</ci><ci>S</ci></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t13",
          "expression": "365.0*I_2p*R0_2*S/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_2p</ci><ci>R0_2</ci><ci>S</ci></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t14",
          "expression": "365.0*I_1*R0_1*R_2*(1 - psi)/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_1</ci><ci>R0_1</ci><ci>R_2</ci><apply><minus/><cn>1</cn><ci>psi</ci></apply></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t15",
          "expression": "365.0*I_1p*R0_1*R_2*(1 - psi)/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_1p</ci><ci>R0_1</ci><ci>R_2</ci><apply><minus/><cn>1</cn><ci>psi</ci></apply></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t16",
          "expression": "365.0*I_2*R0_2*R_1*(1 - psi)/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_2</ci><ci>R0_2</ci><ci>R_1</ci><apply><minus/><cn>1</cn><ci>psi</ci></apply></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t17",
          "expression": "365.0*I_2p*R0_2*R_1*(1 - psi)/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365.0</cn><ci>I_2p</ci><ci>R0_2</ci><ci>R_1</ci><apply><minus/><cn>1</cn><ci>psi</ci></apply></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t18",
          "expression": "365*I_1/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365</cn><ci>I_1</ci></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t19",
          "expression": "365*I_2/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365</cn><ci>I_2</ci></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t20",
          "expression": "365*I_1p/tInf_1",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365</cn><ci>I_1p</ci></apply><ci>tInf_1</ci></apply>"
        },
        {
          "target": "t21",
          "expression": "365*I_2p/tInf_2",
          "expression_mathml": "<apply><divide/><apply><times/><cn>365</cn><ci>I_2p</ci></apply><ci>tInf_2</ci></apply>"
        },
        {
          "target": "t22",
          "expression": "R_1/tImm",
          "expression_mathml": "<apply><divide/><ci>R_1</ci><ci>tImm</ci></apply>"
        },
        {
          "target": "t23",
          "expression": "R_2/tImm",
          "expression_mathml": "<apply><divide/><ci>R_2</ci><ci>tImm</ci></apply>"
        },
        {
          "target": "t24",
          "expression": "R_p/tImm",
          "expression_mathml": "<apply><divide/><ci>R_p</ci><ci>tImm</ci></apply>"
        }
      ],
      "initials": [],
      "parameters": [
        {
          "id": "N",
          "value": 1
        },
        {
          "id": "l_e",
          "value": 50,
          "units": {
            "expression": "year",
            "expression_mathml": "<ci>year</ci>"
          }
        },
        {
          "id": "R0_1",
          "value": 17,
          "units": {
            "expression": "1",
            "expression_mathml": "<cn>1</cn>"
          }
        },
        {
          "id": "tInf_1",
          "value": 21,
          "units": {
            "expression": "day",
            "expression_mathml": "<ci>day</ci>"
          }
        },
        {
          "id": "R0_2",
          "value": 17,
          "units": {
            "expression": "1",
            "expression_mathml": "<cn>1</cn>"
          }
        },
        {
          "id": "tInf_2",
          "value": 21,
          "units": {
            "expression": "day",
            "expression_mathml": "<ci>day</ci>"
          }
        },
        {
          "id": "psi",
          "value": 0.2,
          "units": {
            "expression": "1",
            "expression_mathml": "<cn>1</cn>"
          }
        },
        {
          "id": "tImm",
          "value": 20,
          "units": {
            "expression": "year",
            "expression_mathml": "<ci>year</ci>"
          }
        }
      ],
      "observables": [],
      "time": {
        "id": "t"
      }
    }
  },
  "metadata": {
    "annotations": {
      "license": "CC0",
      "authors": [],
      "references": [
        "pubmed:16615206"
      ],
      "time_scale": "",
      "time_start": "",
      "time_end": "",
      "locations": [],
      "pathogens": [
        "ncbitaxon:520"
      ],
      "diseases": [
        "doid:1116"
      ],
      "hosts": [
        "ncbitaxon:9606"
      ],
      "model_types": [
        "mamo:0000046"
      ]
    }
  },
  "header": {
    "name": "BIOMD0000000249",
    "description": "BioModels model BIOMD0000000249 processed using MIRA.",
    "schema": "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/petrinet_v0.5/petrinet/petrinet_schema.json",
    "schema_name": "petrinet",
    "model_version": "1.0"
  }
}
example_model_description_2={
    "id": "caa8e487-3db2-4d3a-bc28-7df0d28ac9f7",
    "timestamp": "2023-07-08T01:22:08",
    "header": {
      "name": "Giordano2020 - SIDARTHE model of COVID-19 spread in Italy",
      "description": "BioModels model BIOMD0000000955 processed using MIRA.",
      "schema": "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/petrinet_v0.5/petrinet/petrinet_schema.json",
      "schema_name": "petrinet",
      "model_version": "1.0"
    },
    "username": ""
  }
example_dataset_description={'_index': 'tds_dataset',
 '_id': '0fe1cf32-305d-41fa-8810-3647c9031d45',
 '_score': None,
 'sort': [None],
 'id': '0fe1cf32-305d-41fa-8810-3647c9031d45',
 'timestamp': '2023-07-17 17:22:43',
 'username': 'Brandon Rose',
 'name': 'Test data with document',
 'description': 'Test data',
 'data_source_date': '2022-10-01T12:00:00',
 'file_names': ['dataset.csv'],
 'dataset_url': None,
 'columns': [{'name': 'timestamp',
   'data_type': 'float',
   'description': 'The time at which the data was recorded',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'timestamp',
    'concept': 'Time',
    'unit': 'Seconds',
    'description': 'The time at which the data was recorded',
    'column_stats': {'mean': 44.5,
     'std': '26.124700955226263',
     'min': 0,
     '25%': 22.25,
     '50%': 44.5,
     '75%': 66.75,
     'max': 89,
     'type': 'numeric'},
    'groundings': {'identifiers': {'pato:0000165': 'time',
      'gfo:Time': 'time',
      'geonames:2365173': 'Maritime',
      'wikidata:Q174728': 'centimeter',
      'probonto:k0000056': 'nondecisionTime',
      'wikidata:Q186885': 'timestamp',
      'wikidata:Q186868': 'timestamp-based concurrency control',
      'wikidata:Q7804853': 'TimeSTAMP protein labelling',
      'wikidata:Q7806609': 'Timestamping',
      'wikidata:Q119830484': 'Timestamp unit and communication control unit for a user station of a communication network'}}},
   'grounding': None},
  {'name': 'Ailing',
   'data_type': 'float',
   'description': 'The proportion of the population that is ailing',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Ailing',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that is ailing',
    'column_stats': {'mean': '0.009008152668129913',
     'std': '0.014786161655437823',
     'min': '3.983930696449534e-7',
     '25%': '0.00025955101591532495',
     '50%': '0.0009730515594128',
     '75%': '0.0100854465272277',
     'max': '0.0499324910342693',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'wikidata:Q96191575': 'Àilíng',
      'wikidata:Q81903296': 'Ailing',
      'wikidata:Q96274105': 'Ǎilíng',
      'wikidata:Q106390641': 'Ailing',
      'wikidata:Q110273265': 'Ailing'}}},
   'grounding': None},
  {'name': 'Diagnosed',
   'data_type': 'float',
   'description': 'The proportion of the population that has been diagnosed with a disease',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Diagnosed',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that has been diagnosed with a disease',
    'column_stats': {'mean': '0.0394178779872441',
     'std': '0.05404052772243545',
     'min': '0.0000010311159712728113',
     '25%': '0.0018283768440596',
     '50%': '0.00929199671372765',
     '75%': '0.0601336536929011',
     'max': '0.1707891523838043',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'ncit:C113725': 'Undiagnosed',
      'ncit:C15220': 'Diagnosis',
      'ncit:C25587': 'Newly Diagnosed',
      'symp:0000527': 'undiagnosed cardiac murmur',
      'ndfrt:N0000003966': 'Mental Disorders Diagnosed in Childhood [Disease/Finding]'}}},
   'grounding': None},
  {'name': 'Extinct',
   'data_type': 'float',
   'description': 'The proportion of the population that has gone extinct',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Extinct',
    'concept': 'Population Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that has gone extinct',
    'column_stats': {'mean': '0.01946838617206812',
     'std': '0.02435992336039277',
     'min': '1.727546057594953e-11',
     '25%': '0.00000975724651652854',
     '50%': '0.0054324809461831994',
     '75%': '0.03683998435735695',
     'max': '0.075444646179676',
     'type': 'numeric'},
    'groundings': {'identifiers': {'wikidata:Q112937556': 'Population status and genetic diversity of the endemic black-billed gull Larus bulleri of New Zealand',
      'wikidata:Q51520227': 'Population status and ecology of trembling aspen and black cottonwood communities on the Blackfeet Indian Reservation',
      'wikidata:Q51520231': 'Population status of California sea otters',
      'wikidata:Q57268998': 'Population status, trends and a re-examination of the hypotheses explaining the recent declines of the southern elephant seal Mirounga leonina',
      'wikidata:Q57942512': 'Population status of the Bornean orang-utan (Pongo pygmaeus) in the Sebangau peat swamp forest, Central Kalimantan, Indonesia',
      'hp:0000550': 'Undetectable electroretinogram'}}},
   'grounding': None},
  {'name': 'Healed',
   'data_type': 'float',
   'description': 'The proportion of the population that has healed from a disease',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Healed',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that has healed from a disease',
    'column_stats': {'mean': '0.22938889057774314',
     'std': '0.20447154399907744',
     'min': '1.582136377464849e-7',
     '25%': '0.002488563477527275',
     '50%': '0.22360456734895706',
     '75%': '0.42947647720575327',
     'max': '0.5455223917961121',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'wikidata:Q27818491': 'Healed by Metal',
      'wikidata:Q18290529': 'Healedet, Kleva 1:1',
      'wikidata:Q27045018': 'Healed by Horses',
      'wikidata:Q65401451': 'HeaLED: Pilot Study of Skin Healing Under LED Exposure',
      'wikidata:Q93785266': 'Healed microfracture orientations in granites from the Basin and Range Province, western Utah and eastern Nevada and their relationship to paleostresses'}}},
   'grounding': None},
  {'name': 'Infected',
   'data_type': 'float',
   'description': 'The proportion of the population that is infected with a disease',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Infected',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that is infected with a disease',
    'column_stats': {'mean': '0.02790488618460985',
     'std': '0.048876102449425356',
     'min': '0.0000046258805923571344',
     '25%': '0.0007576048810733',
     '50%': '0.0025655663339420503',
     '75%': '0.027287089265882924',
     'max': '0.1739306598901748',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'ido:0000511': 'infected population',
      'efo:0001460': 'uninfected',
      'vsmo:0000268': 'infected',
      'doid:13117': 'paronychia',
      'idomal:0001129': 'RESA-155'}}},
   'grounding': None},
  {'name': 'Recognized',
   'data_type': 'float',
   'description': 'The proportion of the population that has been recognized as having a disease',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Recognized',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that has been recognized as having a disease',
    'column_stats': {'mean': '0.13339161104932754',
     'std': '0.11763891104284653',
     'min': '1.730537206867666e-7',
     '25%': '0.00406794954324135',
     '50%': '0.1140047647058963',
     '75%': '0.2387948259711265',
     'max': '0.332558125257492',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'pr:O43290': 'U4/U6.U5 tri-snRNP-associated protein 1 (human)',
      'pr:Q13084': '39S ribosomal protein L28, mitochondrial (human)',
      'pr:Q15020': 'squamous cell carcinoma antigen recognized by T-cells 3 (human)'}}},
   'grounding': None},
  {'name': 'Susceptible',
   'data_type': 'float',
   'description': 'The proportion of the population that is susceptible to a disease',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Susceptible',
    'concept': 'Health Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that is susceptible to a disease',
    'column_stats': {'mean': '0.43978654684291946',
     'std': '0.3875698850845855',
     'min': '0.1164822503924369',
     '25%': '0.12271593324840067',
     '50%': '0.16231215745210645',
     '75%': '0.9662239998579025',
     'max': '0.9999932050704956',
     'type': 'numeric'},
    'groundings': {'identifiers': {'hp:0032319': 'Health status',
      'ido:0000514': 'susceptible population',
      'apollosv:00000205': 'susceptible organism',
      'ido:0000659': 'susceptible organism',
      'apollosv:00000234': 'susceptible population',
      'cemo:susceptible_individuals': 'susceptible individuals'}}},
   'grounding': None},
  {'name': 'Threatened',
   'data_type': 'float',
   'description': 'The proportion of the population that is threatened',
   'format_str': None,
   'annotations': [],
   'metadata': {'col_name': 'Threatened',
    'concept': 'Population Status',
    'unit': 'Proportion',
    'description': 'The proportion of the population that is threatened',
    'column_stats': {'mean': '0.10163357534429503',
     'std': '0.09215792633301328',
     'min': '5.817323067702773e-9',
     '25%': '0.00043687596189552496',
     '50%': '0.09806311875581736',
     '75%': '0.20163438096642491',
     'max': '0.2144329398870468',
     'type': 'numeric'},
    'groundings': {'identifiers': {'wikidata:Q112937556': 'Population status and genetic diversity of the endemic black-billed gull Larus bulleri of New Zealand',
      'wikidata:Q51520227': 'Population status and ecology of trembling aspen and black cottonwood communities on the Blackfeet Indian Reservation',
      'wikidata:Q51520231': 'Population status of California sea otters',
      'wikidata:Q57268998': 'Population status, trends and a re-examination of the hypotheses explaining the recent declines of the southern elephant seal Mirounga leonina',
      'wikidata:Q57942512': 'Population status of the Bornean orang-utan (Pongo pygmaeus) in the Sebangau peat swamp forest, Central Kalimantan, Indonesia',
      'wikidata:Q6146206': 'Threatened',
      'wikidata:Q335214': 'endangered language',
      'wikidata:Q10889918': 'threatened abortion',
      'wikidata:Q16197023': 'threatened species',
      'wikidata:Q590861': 'World Conservation Monitoring Centre'}}},
   'grounding': None}],
 'metadata': None,
 'source': None,
 'grounding': None}

class ChromaPlus(Chroma):
    def similarity_search_by_vector_with_score(
      self,
      embedding: List[float],
      k: int = DEFAULT_K,
      filter: Optional[Dict[str, str]] = None,
      where_document: Optional[Dict[str, str]] = None,
      **kwargs: Any,
  ) -> List[Document]:
      """Return docs most similar to embedding vector.
      Args:
          embedding (List[float]): Embedding to look up documents similar to.
          k (int): Number of Documents to return. Defaults to 4.
          filter (Optional[Dict[str, str]]): Filter by metadata. Defaults to None.
      Returns:
          List of Documents most similar to the query vector.
      """
      results = self.__query_collection(
          query_embeddings=embedding,
          n_results=k,
          where=filter,
          where_document=where_document,
      )
      return _results_to_docs_and_scores(results)
  
    @xor_args(("query_texts", "query_embeddings"))
    def __query_collection(
      self,
      query_texts: Optional[List[str]] = None,
      query_embeddings: Optional[List[List[float]]] = None,
      n_results: int = 4,
      where: Optional[Dict[str, str]] = None,
      where_document: Optional[Dict[str, str]] = None,
      **kwargs: Any,
  ) -> List[Document]:
      """Query the chroma collection."""
      try:
          import chromadb  # noqa: F401
      except ImportError:
          raise ValueError(
              "Could not import chromadb python package. "
              "Please install it with `pip install chromadb`."
          )
      return self._collection.query(
          query_texts=query_texts,
          query_embeddings=query_embeddings,
          n_results=n_results,
          where=where,
          where_document=where_document,
          **kwargs,
      )

def get_model_info(model_id):
    """
    
    Call get model info tds api
    tds api only allows to call one model_id at a time

    """
    import requests
    base="https://data-service.staging.terarium.ai/models/"
    end=f'{model_id}'
    headers = {
    "accept": "application/json",
    }
    res=requests.get(base+end)
    out=res.json()
    #not using these for now
    out.pop("timestamp")
    out.pop("semantics")
    return out

def get_model_refs(pubmed_ref):
    """
    

    Parameters
    ----------
    pubmed_ref : str
        Pubmed identifier in the form of 123424512

    Returns
    -------
    {"article_title":str,"abstract":str}
    Returns the name and abstract strings for the pubmed article

    """
    import requests
    from bs4 import BeautifulSoup
    try:
        # Construct the URL using the article ID
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_ref}/"

        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status() # Check if the request was successful

        # Parse the webpage content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find and extract the article title and author name
        article_title = soup.find('h1', class_='heading-title').get_text(strip=True)

        # Find and extract the abstract
        abstract_section = soup.find('div', class_='abstract-content selected')
        if abstract_section:
            abstract_text = abstract_section.get_text(strip=True)
        else:
            abstract_text = "Abstract not found"

        return {"article_title": article_title, "abstract": abstract_text}
    except requests.exceptions.RequestException as e:
        return f"Failed to retrieve the webpage: {e}"
    except AttributeError as e:
        return f"Failed to extract data from the webpage: {e}"

def prettify(ranked_list):
    """takes a list of tuples of (document:Document, score:float), gets some 
    information and puts it into a format for response"""
    
    return [{'dataset_id':feature[0].metadata['object_id'],
             'feature_name':feature[0].metadata['name'],
             'score':feature[1]} for feature in ranked_list]

#main endpoint
def find_dataset_features(model_id,feature_name=None,dataset_ids=None):
    """
    Match model to features in given datasets
    
    Model ID is a string that will be used to find the model embedding. The model id should be the same as in the tds database and metadata in the vectorstore 
    If the model embedding doesn't exist we will embed it
    
    If a feature name is listed only get the dataset features for that feature 
    in the model, we will return ranked lists for each feature in the model
    
    Datasets is a list of dataset ids. These ids are used to filter the dataset of embeddings.
    If dataset ids is None then try all datasets.
    
    Returns a dictonary of ranked lists with each key being a feature name requested. 
    Note that for the scores listed in the ranked lists higher is worse.
    
    Example Usage: 
        #all dataset case - 
        dataset_features=find_dataset_features('biomd0000000249-model-id')
        #few datasets case - 
        dataset_features=find_dataset_features('biomd0000000249-model-id',dataset_ids=['0fe1cf32-305d-41fa-8810-3647c9031d45','de6be6cb-b9a0-4959-b5c6-3745576adfc3','6d8cab47-e206-4b50-a745-2bda112d0892'])
        # for a specific feature
        dataset_features=find_dataset_features('biomd0000000249-model-id',feature_name='S')
        
    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.document_loaders import TextLoader
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    
    #load vector store - 
    fs = LocalFileStore("./cache/")
    #embedder=OpenAIEmbeddings(openai_api_key=openai_api_key)
    embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='all-MiniLM-L6-v2'
    )
    
    vectorstore=ChromaPlus(persist_directory="./chroma_db", embedding_function=cached_embedder)
    model_info=get_model_info(model_id)
    model_embeds=vectorstore.get(where={'object_id':model_id})
    if len(model_embeds['ids'])==0:embed([model_info]) #if model is not embedded, embed it now.
    results={}
    #to parallelize
    #fix multiple calls to vector store
    #could add further filters to make more efficient based on the feature..
    for feature in model_info['model']['states']:
        if feature_name is not None:
            if feature['name'] not in feature_name:continue
        filter_terms={"$and":[{"object_type": {
            "$eq": 'model'
        }},{"object_id": {
            "$eq": model_id
        }},
           {"name": {
               "$eq": feature['name']
           }} ]}    
        feature_embed = vectorstore.get(where=filter_terms,include=['embeddings', 'documents', 'metadatas'])['embeddings']
        #filter by feature
        #find matches in vector store using object_ids filter
        if dataset_ids==None:
            filter_terms={"object_type": {
                "$eq": 'dataset'
            }}
            top_k_dataset_features=vectorstore.similarity_search_by_vector_with_score(feature_embed,filter=filter_terms, k=5)
        else:
            if len(dataset_ids)==1:
                filter_terms={"$and":[{"object_type": {
                    "$eq": 'dataset'
                }},{"object_id": {
                    "$eq": dataset_ids[0]
                }}]}
            else:
                filter_terms={"$and":[{"object_type": {
                    "$eq": 'dataset'
                }},{"$or":[]}]}
                for dataset_id in dataset_ids:
                    filter_terms['$and'][1]['$or'].append(
                    {
                    "object_id": {
                        "$eq": dataset_id
                    }
                    })
            top_k_dataset_features=vectorstore.similarity_search_by_vector_with_score(feature_embed, filter=filter_terms,k=5)
        
        #post process pretty result
        pretty_result = prettify(top_k_dataset_features)
        results[feature['name']]=pretty_result
    return results

def fetch_groundings(groundings_ids):
    import requests
    base = "http://34.230.33.149:8771/api"
    #res = requests.get(base + f"/lexical/{query}")
    if type(groundings_ids)!=list:groundings_ids=[groundings_ids]
    groundings_ids=','.join(groundings_ids)
    res=requests.get(base+ f"/entities/{groundings_ids}")
    #sort groundings info
    if res.status_code == 200:
        groundings_info=res.json()
    else:
        groundings_info="error" #to do: add error passing or warning...
    return groundings_info
    
#second endpoint?
def embed(objects:List[Dict]): #dataset)
    """
    Takes a list of objects (models or datasets) and their object type in a dict format and embeds their features in the vector store
    Inputs:
        objects: List[Dict] = List of objects to be embedded in format -  [{'info':object_dict,'type':'model' or 'dataset'}]
    Outputs:
        retriever - langchain retriever object
    
    Example usage:
        vs=embed([{"info":example_model_get},'type':'model'])
    
    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    
    #load huggingface embedder or openai embedder
    fs = LocalFileStore("./cache/")
    #embedder=OpenAIEmbeddings(openai_api_key=openai_api_key)
    embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='all-MiniLM-L6-v2'
    )
    
    #format templates
    # to do: add in bulk/parallel
    # to do: add ifs, probably at least one if for groundings semantic similiarity etc..
    # to do: add try excepts. etc..
    text_chunks=[] #build text chunks
    metadatas=[] #build metadatas
    for obj in objects:
        if obj['type']=='dataset':
            object_info=obj['info']
            #create chunks in parallel
            for feature in object_info['columns']:
                #to do: add try, excepts, etc..
                text_chunk = DATASET_TEMPLATE.format(obj_name=object_info['name'],
                                                    obj_description=object_info['description'],
                                                    column_name=feature['name'],
                                                    column_description=feature['description'],
                                                    column_data_type=feature['data_type'],
                                                    column_units=feature['metadata']['unit'],
                                                    column_concept=feature['metadata']['concept'],
                                                    column_column_stats= ', '.join(f'{k}={v}' for k, v in feature['metadata']['column_stats'].items()))
                metadata={'name':feature['name'],'object_id':object_info['id'],'object_type':obj['type']}
                groundings_info=fetch_groundings(list(feature['metadata']['groundings']['identifiers'].keys())) #fetch one at a time??
                if 'error' != groundings_info:
                    if 'grounding' in feature.keys() and feature['grounding'] is not None:
                        grounding_info = fetch_groundings(feature['grounding'])
                        groundings_info+=grounding_info
                    
                    ground_chunks=[]
                    for grounding_info in groundings_info:
                        ground_chunk=GROUND_CHUNK_TEMPLATE.format(ground_name=grounding_info['name'],
                                                                  ground_description=grounding_info['description'] if 'description' in grounding_info else grounding_info['name'],
                                                                  ground_synonyms='\n'.join([syn['value'] for syn in grounding_info['synonyms']]))
                        ground_chunks.append(ground_chunk)
                    #add groupings chunks
                    if len(ground_chunks)>0:
                        text_chunk+="\n\n Here are a list of related topics to the feature being described:"
                        text_chunk+='\n'.join(ground_chunks)
                print(f"Feature {feature['name']} on model {object_info['name']} was embedded")
                text_chunks.append(text_chunk)
                metadatas.append(metadata)
            
        elif obj['type'] == 'model': 
            object_info=obj['info']
            for feature in object_info['model']['states']:
                text_chunk=MODEL_TEMPLATE.format(obj_name=object_info['header']['name'],obj_description=object_info['header']['description'])
                metadata={'name':feature['name'],'object_id':object_info['id'],'object_type':obj['type']}
                
                #add extra model info if it is there
                if 'references' in object_info['metadata']['annotations']:
                    for ref in object_info['metadata']['annotations']['references']:
                        references=get_model_refs(ref.lstrip('pubmed:'))
                        if type(references)==str:continue
                        text_chunk+="Here are the contents of a reference article on the model:"
                        text_chunk+=f"\nTitle:{references['article_title']}"
                        text_chunk+=f"\nAbstract:{references['abstract']}"
                for term in ['pathogens','diseases','hosts']: #generalize later (add something about it being an epidemiology model to prompt?)
                    if term in object_info['metadata']['annotations']:
                        print(object_info['metadata']['annotations'][term])
                        groundings_info=fetch_groundings(object_info['metadata']['annotations'][term])
                        if 'error' != groundings_info:
                            text_chunk+=f"\n\n Here is some information on the {term} being modeled:"
                            for grounding_info in groundings_info:
                                ground_chunk=GROUND_CHUNK_TEMPLATE.format(ground_name=grounding_info['name'],
                                                                      ground_description=grounding_info['description'] if 'description' in grounding_info else grounding_info['name'],
                                                                      ground_synonyms='\n'.join([syn['value'] for syn in grounding_info['synonyms']]))
                                text_chunk+=ground_chunk
                # to do: use model type later?
                #create chunks in parallel
                # to do: throw error if no grounding for model feature or grounding can't be found?
                ground_chunks=[]
                groundings_info = fetch_groundings([f"{key}:{value}" for key, value in feature['grounding']['identifiers'].items()])
                if type(groundings_info)==str:groundings_info=[groundings_info]
                for grounding_info in groundings_info:
                    try:
                        ground_chunk=GROUND_CHUNK_TEMPLATE.format(ground_name=grounding_info['name'],
                                                                  ground_description=grounding_info['description'] if 'description' in grounding_info else grounding_info['name'],
                                                                  ground_synonyms='\n'.join([syn['value'] for syn in grounding_info['synonyms']]))
                        ground_chunks.append(ground_chunk)
                    except:
                        continue #to do: add warning
                    
                #add groupings chunks
                if len(ground_chunks)>0:
                    text_chunk+="\nHere are a list of related topics to the feature being described:\n"
                    text_chunk+='\n'.join(ground_chunks)
                    text_chunks.append(text_chunk)
                    metadatas.append(metadata)
                    print(f"Feature {feature['name']} on model {object_info['header']['name']} was embedded")
                else:
                    print(f"Feature {feature['name']} on model {object_info['header']['name']} could not be embedded because there are no groundings that could be found")
    
    #documents to store and embed
    vectorstore=ChromaPlus(persist_directory="./chroma_db", embedding_function=cached_embedder) #load
    vectorstore.add_texts(texts=text_chunks,metadatas=metadatas)
    
    return vectorstore
    
def evaluate_query(model_id,feature_name=None,dataset_ids=None):
    """
    Evalutes a query's results given a model id in the evaluation dataset
    and optionally a number of dataset_ids.
    Looks through the ranking of the document features and compares with query results (top k)
    """
    pass