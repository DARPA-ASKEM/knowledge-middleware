# -*- coding: utf-8 -*-
"""
This file contains code for evaluating model to document matching and
model feature to dataset feature matching and generating evaluation datasets.
"""

from embed import document_embed,short_feature_embed,long_feature_embed
from find import (find_dataset_semantic_matching,
                  find_dataset_features_hierarchical,
                  find_dataset_features_basic_llm_query_1,
                  find_dataset_features_semantic_matching)

def get_dataset_card(gpt_key,csv_file,doc_file):
    import requests

    url = "http://54.227.237.7/cards/get_data_card"
    params = {
        "gpt_key": gpt_key,
        "smart": "true"
    }
    headers = {
        "accept": "application/json",
    }
    files = {
        "csv_file": (csv_file, open(csv_file, "rb"), "text/csv"),
        "doc_file": (doc_file, open(doc_file, "rb"), "application/pdf")
    }
    
    response = requests.post(url, headers=headers, params=params, files=files)
    
    if response.status_code==200:
        return response.json()
    else:
        return f"Error occurred. Status code: {response.status_code}"
    
def create_tds_dataset(data_dict):
    import requests
    url="https://data-service.staging.terarium.ai/datasets/"
    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json=data_dict)

    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    else:
        return f"Error occurred. Status code: {response.status_code}"
    
def create_tds_model(model_dict):
    import requests
    url="https://data-service.staging.terarium.ai/models/"
    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=model_dict)
    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    else:
        return f"Error occurred. Status code: {response.status_code}"
    
def generate_grounding_from_list(list_of_text):
    """
    Generate groundings for a list of texts
    
    example usage:
    data = ["Infected Population", "Breast Cancer"]
    generate_grounding_from_list(data)
    
    """
    import requests
    for i,text in enumerate(list_of_text):
        list_of_text[i]={"text":text}
    url = 'http://34.230.33.149:8771/api/ground_list'
    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=list_of_text)
    if response.status_code == 200 or response.status_code == 201:
        res=response.json()
        print(response.json())
        groundings={'identifiers':{}}
        for re in res:
            for r in re['results']:
                groundings['identifiers'][r['curie']]=r['name']
        return groundings
    else:
        return f"Error occurred. Status code: {response.status_code}"
    
def get_dataset_info_from_source(source):
    """
    Use cdc website to get dataset info
    source is a string containing a webpage url
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from sodapy import Socrata
    import pandas as pd
    #get sodapy identifier
    sodapy_identifier=source.split('/')[-1]
    #sodapy_identifier="9bhg-hcku"
    
    client = Socrata("data.cdc.gov",None)
    csv = client.get(sodapy_identifier)
    #save csv to tmp/local
    csv=pd.DataFrame(csv)
    csv.to_csv(f'./eval_dataset/{sodapy_identifier}.csv')
    metadata = client.get_metadata(sodapy_identifier)
    dataset_info={'name':metadata['name'],'description':metadata['description'],
                  'file_names':['dataset.csv'],'columns':[]}
    enum_values=["unknown","boolean","string","integer","float","double","timestamp","datetime","date","time"]
    datatype_converter={
        'text':'string',
        'calendar_date':'date',
        'number':'float',
        'url':'string',
        'checkbox':'boolean',
        'location':'string'}
    for dtype in enum_values:datatype_converter[dtype]=dtype
    # to do :convert types
    for col in metadata['columns']:
        dataset_info['columns'].append({'name':col['name'],
                                        'data_type':datatype_converter[col['dataTypeName']],
                                        'description':col['description'] if 'description' in col.keys() else col['name'],
                                        'concept':'',
                                        'metadata':{'col_name':col['fieldName'],
                                                    'unit':'',
                                                    'column_stats':{}},
                                        'annotations':[]
                                        })
    #build pdf
    pdf_path = f"./eval_dataset/{sodapy_identifier}.pdf"
    document = SimpleDocTemplate(pdf_path, pagesize=letter)
    content=[]
    content.append(Paragraph(metadata['name']))
    content.append(Paragraph(metadata['description']))
    document.build(content)
    
    return dataset_info,f'./eval_dataset/{sodapy_identifier}.csv',f'./eval_dataset/{sodapy_identifier}.pdf'

def create_model_via_mira(option):
    from copy import deepcopy as _d
    import sympy
    import requests
    from mira.metamodel import (ControlledConversion, NaturalConversion, 
        GroupedControlledConversion, TemplateModel, Initial, Parameter, 
        safe_parse_expr, Unit)
    from mira.examples.concepts import (susceptible, infected, recovered, infected_symptomatic,
        infected_asymptomatic)
    from mira.metamodel import Concept
    rest_url = "http://34.230.33.149:8771"
    #concepts-
    susceptible = Concept(name="susceptible_population", identifiers={"ido": "0000514"})
    infected = Concept(name="infected_population", identifiers={"ido": "0000511"})
    infected_symptomatic = infected.with_context(status="symptomatic")
    infected_asymptomatic = infected.with_context(status="asymptomatic")
    recovered = Concept(name="immune_population", identifiers={"ido": "0000592"})
    exposed = susceptible.with_context(property="ido:0000597")
    dead = Concept(name="dead", identifiers={"ncit": "C28554"})
    hospitalized = Concept(name="hospitalized", identifiers={"ncit": "C25179"})
    vaccinated = Concept(name="vaccinated", identifiers={"vo": "0001376"})
    
    concepts=[susceptible,infected,infected_symptomatic,infected_asymptomatic,
              recovered,exposed,dead,hospitalized,vaccinated]
    # Model
    import random

    num_nodes = random.randint(3, 7)
    nodes=[]
    for node in range(num_nodes):
        node_type=random.randint(0, len(concepts))
        
        #Drisana Iverson
        
    infection = ControlledConversion(
        subject=susceptible,
        outcome=infected,
        controller=infected,
    )
    recovery = NaturalConversion(
        subject=infected,
        outcome=recovered,
    )
    model = TemplateModel(
        templates=[
            infection,
            recovery,
        ],
    )
    res = requests.post(rest_url + "/api/to_petrinet", json=model.dict())
    if res.status_code == 200:
        model=res.json()
    else:
        model=f"Error occurred. Status code: {res.status_code}"
    
    return model


def create_eval_models():
    from mira.examples import sir
    import requests
    models=[sir.sir]
    # models=[sir.sir,sir.parameterized,sir.sir2_city,sir.svir]
    rest_url = "http://34.230.33.149:8771"
    eval_models=[]
    for model in models:
        res = requests.post(rest_url + "/api/to_petrinet", json=model.dict())
        res_model=res.json()
        res_model['header']={
            "name": res_model['name'],
            "schema": res_model['schema'],
            "description": res_model['description'],
            "model_version": res_model['model_version']
          }
        eval_models.append(res_model)
    return eval_models

def get_model_card(gpt_key,text_file,code_file):
    import requests

    url = "http://54.227.237.7/cards/get_data_card"
    params = {
        "gpt_key": gpt_key,
        "smart": "true"
    }
    headers = {
        "accept": "application/json",
    }
    files = {
        "text_file": (text_file, open(text_file, "rb"), "text/csv"),
        "code_file": (code_file, open(code_file, "rb"), "application/pdf")
    }
    
    response = requests.post(url, headers=headers, params=params, files=files)
    
    if response.status_code==200:
        return response.json()
    else:
        return f"Error occurred. Status code: {response.status_code}"
    
feature_eval_datasets=[{'source':'https://data.cdc.gov/NCHS/Provisional-COVID-19-Deaths-by-Sex-and-Age/9bhg-hcku'},
               {'source':'https://data.cdc.gov/Flu-Vaccinations/Vaccines-gov-Flu-vaccinating-provider-locations/bugr-bbfr'},
               {'source':'https://data.cdc.gov/Vaccinations/COVID-19-Vaccinations-in-the-United-States-Jurisdi/unsk-b7fc'},
               {'source':'https://data.cdc.gov/Public-Health-Surveillance/United-States-COVID-19-Community-Levels-by-County/3nnm-4jni'}]

def generate_feature_eval_dataset(datasets=feature_eval_datasets):
    """
    Generates a new evaluation dataset using a list of dataset_file dictionaries
    
    datasets format:
        [{'name':'Relevant Name','description':'description','csv_file':'csv_data.csv','doc_file':'dataset_paper.pdf','source':'http://source.com/source1'}]
    Alternatively you can provide a cdc source and we will get the rest of the information for you - 
    [{'source':'http://source.com/source1'},{'source':'http://source.com/source2'}]
        
    Using those new data cards, we create a smaller number of models that uses some subset of the features of that dataset
    (and maybe some examples where the datasets don't contain the feature)
     
    Then we get model cards for those new models
    
    We will then create all of these models and datasets in tds
    
    The function returns the models and datasets
    Once this is created you need to go through and manually rank the top 5 dataset features for each model
    The methodology for doing so is find any relevant features. Then find from those features, rank them based on dataset relevance.
    

    Parameters
    ----------
    dataset_files : List[str]
        list of csv file names

    Returns
    -------
    
    eval_dataset : dict. Dict describing the new eval dataset
    The format is {'datasets':[dataset_dict],'models':[model_dict],ground_truth:[]}
    dataset_dict is of format - {'info':dataset_description_tds,'type':'dataset'}
    model_dict is of format  - {'info':model_get_response_tds,'type':'model'}
    ground_truth will be an empty list to be filled out in the format:
    {'model_id':model_id,ranked_lists:{"feature_name_in_model":[{"dataset_id":dataset_id,"feature_name":feature_name}]}}

    """
    from keys import gpt_key
    #process datasets and get info if needed
    for dataset in datasets:
        if len(dataset.keys())==1 and 'source' in dataset.keys():
            #get dataset info from source
            dataset_info,csv_file,doc_file=get_dataset_info_from_source(dataset['source'])
            dataset['csv_file']=csv_file
            dataset['doc_file']=doc_file
            dataset.update(dataset_info)
        else:  
            pass
            #to do: only from source works right now
            #get dataset card
            #dataset_card=get_dataset_card(gpt_key,dataset['csv_file'],dataset['doc_file'])
            
            #add dataset card info to dataset
            #create column info?
            
        #create columns groundings
        for i,col in enumerate(dataset['columns']):
            groundings=generate_grounding_from_list([col['name'],col['description']])
            dataset['columns'][i]['metadata']['groundings']=groundings
            dataset['columns'][i]['grounding']={'identifiers':{}}
            
    models=create_eval_models()
    for model in models:
        #get_model_card(gpt_key,text_file,code_file)
        pass
    #create ground truth template from model states...
    ground_truth=[]
    model_dicts=[]
    dataset_dicts=[]
    for model in models:
        model_id=create_tds_model(model)
        model['id']=model_id['id']
        model_gt={'model_id':model['id'],'ranking_lists':{}}
        for feature in model['model']['states']:
            model_gt['ranking_lists'][feature['name']]=[{'dataset_id':'','feature_name':''}]
        ground_truth.append(model_gt)
        model_dicts.append({'info':model,'type':'model'})
    for dataset in datasets:
        dataset_id=create_tds_dataset(dataset)
        dataset['id']=dataset_id['id']
        dataset_dicts.append({'info':dataset,'type':'dataset'})
    eval_dataset = {'datasets':dataset_dicts,'models':model_dicts,'ground_truth':ground_truth}  
    
    return eval_dataset

def get_feature_ranking_metrics(preds, gts,ks=[1,3,5]):
    """
    preds/gt is in format - 
    {'susceptible_population': [{'dataset_id': '2e25fd89-5034-4a34-8ad2-343f5b49b820',
       'feature_name': 'county_population'},
      {'dataset_id': 'b0f19908-0766-4b90-b5ad-a740e69ebe6a',
       'feature_name': 'Admin_Per_100k_65Plus'},
      {'dataset_id': 'b0f19908-0766-4b90-b5ad-a740e69ebe6a',
       'feature_name': 'Distributed_Per_100k_65Plus'},
      {'dataset_id': '2e25fd89-5034-4a34-8ad2-343f5b49b820',
       'feature_name': 'covid_cases_per_100k'},
      {'dataset_id': '08133270-8a3b-4d65-9126-63cb07b05ec5',
       'feature_name': 'Age Group'}]
     

    """
    metrics={}
    for key in gts.keys():
        metrics[key]={}
        for k in ks:
            if k>len(gts[key]):k=len(gts[key])
            metrics[key][f'precision@{k}']=0
            metrics[key][f'recall@{k}']=0
            metrics[key][f'exact_match@{k}']=0
            
            for i in range(k):
                if gts[key][i]['dataset_id']==preds[key][i]['dataset_id'] and gts[key][i]['feature_name']==preds[key][i]['feature_name']:
                    metrics[key][f'exact_match@{k}']+=1
                for j in range(k):
                    if gts[key][j]['dataset_id']==preds[key][i]['dataset_id'] and gts[key][j]['feature_name']==preds[key][i]['feature_name']:
                        metrics[key][f'precision@{k}']+=1
            for i in range(k):
                for j in range(k):
                    if gts[key][i]['dataset_id']==preds[key][j]['dataset_id'] and gts[key][i]['feature_name']==preds[key][j]['feature_name']:
                        metrics[key][f'recall@{k}']+=1
            
            metrics[key][f'precision@{k}']=metrics[key][f'precision@{k}']/k if metrics[key][f'precision@{k}']!=0 else 0
            metrics[key][f'recall@{k}']=metrics[key][f'recall@{k}']/k if metrics[key][f'recall@{k}']!=0 else 0
            metrics[key][f'exact_match@{k}']=metrics[key][f'exact_match@{k}']/k if metrics[key][f'exact_match@{k}']!=0 else 0

    return metrics
    
def evaluate_on_feature_finding_eval_dataset(eval_dataset,db_dir="./eval_dataset_chroma_db",
                                             embed_method="short",embed=True,
                                             find_method="basic_llm_query"):
    """
    Evaluation code for finding dataset features given model features (non-hierarchical)
    eval_dataset: Dataset of Models/Dataset to evaluate on. Currently each model
    will be evaluated against all datasets.
    embed_method - Method on how to embed features, options are short and long
    embed: boolean: Whether or not to embed
    find_method - Method on how to find features, options are basic_llm_query and semantic
    
    Example Usage:
        First load the evaluation dataset saved in json - 
        one_to_one_features=json.load(open("./eval_datasets/one_to_one_features.json","r"))
        Then choose your methods (embed and find), choose a directory to save the db_results and run - 
        evaluate_on_feature_finding_eval_dataset(one_to_one_features,"./demo_eval/llm",
                                                 embed_method="short",find_method="basic_llm_query")
        evaluate_on_feature_finding_eval_dataset(one_to_one_features,"./demo_eval/semantic",
                                                 embed_method="short",find_method="semantic")

    """
    import os
    os.makedirs(db_dir,exist_ok=True)
    if embed:
        if embed_method=="short":
            vs=short_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
        elif embed_method=="long":
            vs=long_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    evaluation_scores=[]
    for model in eval_dataset['models']:
        if find_method=="llm_basic_query":
            pred_ranking=find_dataset_features_basic_llm_query_1(model['info']['id'],db_dir=db_dir)
        elif find_method=="semantic":
            pred_ranking=find_dataset_features_semantic_matching(model['info']['id'],db_dir=db_dir)
        gt_ranking=[d for d in eval_dataset['ground_truth'] if d["model_id"] == model['info']['id']][0]['ranking_lists']
        scores=get_feature_ranking_metrics(pred_ranking,gt_ranking)
        evaluation_scores.append({'model_id':model['info']['id'],'scores':scores,'pred':pred_ranking,'gt':gt_ranking})
        
    return evaluation_scores

#one to many documents, sources are saved in json as well.
dataset_eval_datasets=[{'source':'https://data.cdc.gov/Public-Health-Surveillance/United-States-COVID-19-Community-Levels-by-County/3nnm-4jni'},
                       {'source':'https://data.cdc.gov/Policy/The-Tax-Burden-on-Tobacco-1970-2019/7nwe-3aj9'},
                       {'source':'https://data.cdc.gov/Nutrition-Physical-Activity-and-Obesity/CDC-Nutrition-Physical-Activity-and-Obesity-Legisl/nxst-x9p4'},
                       {'source':'https://data.cdc.gov/Traumatic-Brain-Injury-/Rates-of-TBI-related-Deaths-by-Age-Group-United-St/nq6q-szvs'},
                       {'source':'https://data.cdc.gov/Motor-Vehicle/Motor-Vehicle-Occupant-Death-Rate-by-Age-and-Gende/rqg5-mkef'},
                       {'source':'https://data.cdc.gov/Foodborne-Waterborne-and-Related-Diseases/Botulism/66i6-hisz'},
                       {'source':'https://data.cdc.gov/Foodborne-Waterborne-and-Related-Diseases/Development-of-an-Empirically-Derived-Measure-of-F/37nu-tuw8'},
                       {'source':'https://data.cdc.gov/Environmental-Health-Toxicology/Air-Quality-Measures-on-the-National-Environmental/cjae-szjv'},
                       {'source':'https://data.cdc.gov/Environmental-Health-Toxicology/Daily-Census-Tract-Level-PM2-5-Concentrations-2016/7vu4-ngxx'},
                       {'source':'https://data.cdc.gov/Policy-Surveillance/U-S-State-and-Territorial-Public-Mask-Mandates-Fro/62d6-pm5i'},
                       ]

def generate_dataset_eval_dataset(datasets=dataset_eval_datasets):
    """
    Generates a new evaluation dataset using a list of dataset_file dictionaries for evaluating model to dataset matching
    
    datasets format:
        [{'name':'Relevant Name','description':'description','csv_file':'csv_data.csv','doc_file':'dataset_paper.pdf','source':'http://source.com/source1'}]
    Alternatively you can provide a cdc source and we will get the rest of the information for you - 
    [{'source':'http://source.com/source1'},{'source':'http://source.com/source2'}]
        
    Using those new data cards, we create a smaller number of models that uses some subset of the features of that dataset
    (and maybe some examples where the datasets don't contain the feature)
     
    Then we get model cards for those new models
    
    We will then create all of these models and datasets in tds
    
    The function returns the models and datasets
    Once this is created you need to go through and manually rank the top 5 dataset features for each model
    The methodology for doing so is find any relevant features. Then find from those features, rank them based on dataset relevance.
    

    Parameters
    ----------
    dataset_files : List[str]
        list of csv file names

    Returns
    -------
    
    eval_dataset : dict. Dict describing the new eval dataset
    The format is {'datasets':[dataset_dict],'models':[model_dict],ground_truth:[]}
    dataset_dict is of format - {'info':dataset_description_tds,'type':'dataset'}
    model_dict is of format  - {'info':model_get_response_tds,'type':'model'}
    ground_truth will be an empty list to be filled out in the format:
    {'model_id':model_id,ranked_lists:[dataset_id,dataset_id_2,etc..]}

    """
    from keys import gpt_key
    #process datasets and get info if needed
    for dataset in datasets:
        if len(dataset.keys())==1 and 'source' in dataset.keys():
            #get dataset info from source
            dataset_info,csv_file,doc_file=get_dataset_info_from_source(dataset['source'])
            dataset['csv_file']=csv_file
            dataset['doc_file']=doc_file
            dataset.update(dataset_info)
        else:  
            pass
            #to do: only from source works right now
            #get dataset card
            #dataset_card=get_dataset_card(gpt_key,dataset['csv_file'],dataset['doc_file'])
            
            #add dataset card info to dataset
            #create column info?
            
        #create columns groundings
        for i,col in enumerate(dataset['columns']):
            groundings=generate_grounding_from_list([col['name'],col['description']])
            dataset['columns'][i]['metadata']['groundings']=groundings
            dataset['columns'][i]['grounding']={'identifiers':{}}
            
    models=create_eval_models()
    for model in models:
        #get_model_card(gpt_key,text_file,code_file)
        pass
    #create ground truth template from model states...
    ground_truth=[]
    model_dicts=[]
    dataset_dicts=[]
    for model in models:
        model_id=create_tds_model(model)
        model['id']=model_id['id']
        model_gt={'model_id':model['id'],'ranking_lists':{}}
        model_gt['ranking_lists']=[]
        ground_truth.append(model_gt)
        model_dicts.append({'info':model,'type':'model'})
    for dataset in datasets:
        dataset_id=create_tds_dataset(dataset)
        dataset['id']=dataset_id['id']
        dataset_dicts.append({'info':dataset,'type':'dataset'})
    eval_dataset = {'datasets':dataset_dicts,'models':model_dicts,'ground_truth':ground_truth}  
    
    return eval_dataset

def get_dataset_ranking_metrics(preds, gts,ks=[1,3,5]):
    """
    preds/gt is in format - 
    ['2e25fd89-5034-4a34-8ad2-343f5b49b820',
       'b0f19908-0766-4b90-b5ad-a740e69ebe6a',
       ''b0f19908-0766-4b90-b5ad-a740e69ebe6a',
       '2e25fd89-5034-4a34-8ad2-343f5b49b820',
       '08133270-8a3b-4d65-9126-63cb07b05ec5']
     

    """
    metrics={}
    for k in ks:
        if k>len(gts):k=len(gts)
        metrics[f'precision@{k}']=0
        metrics[f'recall@{k}']=0
        metrics[f'exact_match@{k}']=0
        
        for i in range(k):
            if gts[i]==preds[i]:
                metrics[f'exact_match@{k}']+=1
            for j in range(k):
                if gts[j]==preds[i]:
                    metrics[f'precision@{k}']+=1
        for i in range(k):
            for j in range(k):
                if gts[i]==preds[j]:
                    metrics[f'recall@{k}']+=1
        
        metrics[f'precision@{k}']=metrics[f'precision@{k}']/k if metrics[f'precision@{k}']!=0 else 0
        metrics[f'recall@{k}']=metrics[f'recall@{k}']/k if metrics[f'recall@{k}']!=0 else 0
        metrics[f'exact_match@{k}']=metrics[f'exact_match@{k}']/k if metrics[f'exact_match@{k}']!=0 else 0

    return metrics
    

def evaluate_on_dataset_finding_eval_dataset(eval_dataset,db_dir="./eval_dataset_chroma_db",
                                             embed_method="short",embed=True,
                                             find_method="semantic"):
    """
    Evaluation code for finding relevant datasets given a model
    eval_dataset: Dataset of Models/Dataset to evaluate on. Currently each model
    will be evaluated against all datasets.
    db_dir:strWhere to store embeddings, 
    embed_method - Method on how to embed features, options are short
    embed: boolean: Whether or not to embed
    find_method - Method on how to find features, options are semantic 
    
    Example Usage:
        First load the evaluation dataset saved in json - 
        one_to_many_datasets=json.load(open("./eval_datasets/one_to_many_datasets.json","r"))
        Then choose your methods (embed and find), choose a directory to save the db_results and run - 
        evaluate_on_dataset_finding_eval_dataset(one_to_many_datasets,db_dir="./demo_eval/datasets",
                                                 embed_method="short",find_method="semantic")

    """
    import os
    os.makedirs(db_dir,exist_ok=True)
    if embed:
        if embed_method=="short":
            vs=document_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    evaluation_scores=[]
    for model in eval_dataset['models']:
        pred_ranking=find_dataset_semantic_matching(model['info']['id'],db_dir=db_dir)
        gt_ranking=[d for d in eval_dataset['ground_truth'] if d["model_id"] == model['info']['id']][0]['ranking_lists']
        scores=get_dataset_ranking_metrics(pred_ranking,gt_ranking)
        evaluation_scores.append({'model_id':model['info']['id'],'scores':scores,'pred':pred_ranking,'gt':gt_ranking})
        
    return evaluation_scores

def evaluate_on_feature_finding_eval_dataset_hier(eval_dataset,dataset_db_dir="./eval_dataset_chroma_db",
                                                  features_db_dir="./eval_dataset_chroma_db",
                                                  embed=True,feature_embed_method="short",
                                                  document_embed_method="short",
                                                  find_method="semantic"):
    """
    Evaluation code for finding dataset features given model features (hierarchical)
    eval_dataset: Dataset of Models/Dataset to evaluate on. Currently each model
    will be evaluated against all datasets.
    feature_embed_method - Method on how to embed features, options are short and long
    document_embed_method - Method on how to embed features, options are short
    embed: boolean: Whether or not to embed
    find_method - Method on how to find features, options are semantic 
    
    Example Usage:
        First load the evaluation dataset saved in json - 
        one_to_many_features=json.load(open("./eval_datasets/one_to_many_features.json","r"))
        Then choose your methods (embed and find), choose a directory to save the db_results and run - 
        evaluate_on_feature_finding_eval_dataset_hier(one_to_many_features,features_db_dir="./demo_eval/many_features",
                                                 feature_embed_method="short",find_method="semantic",
                                                 document_embed_method="short")

    """
    import os
    os.makedirs(dataset_db_dir,exist_ok=True)
    os.makedirs(features_db_dir,exist_ok=True)
    if embed:
        if feature_embed_method=="short":
            vs=short_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=features_db_dir)
        elif feature_embed_method=="long":
            vs=long_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=features_db_dir)
        if document_embed_method=="short":
            vs=document_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=dataset_db_dir)
    evaluation_scores=[]
    for model in eval_dataset['models']:
        if find_method=="semantic":
            pred_ranking=find_dataset_features_hierarchical(model['info']['id'],dataset_db_dir=dataset_db_dir,features_db_dir=features_db_dir)
        gt_ranking=[d for d in eval_dataset['ground_truth'] if d["model_id"] == model['info']['id']][0]['ranking_lists']
        scores=get_feature_ranking_metrics(pred_ranking,gt_ranking)
        evaluation_scores.append({'model_id':model['info']['id'],'scores':scores,'pred':pred_ranking,'gt':gt_ranking})
        
    return evaluation_scores