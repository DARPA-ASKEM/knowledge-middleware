# -*- coding: utf-8 -*-
"""
This file contains code to embed objects (models,datasets) for model-dataset matching 
and embed features for model-feature - dataset-feature matching
"""
from typing import (List,Dict)
from utils import fetch_groundings,get_model_refs,ChromaPlus

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

def long_feature_embed(objects:List[Dict],db_dir="./chroma_db"): #dataset)
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
    import os
    from keys import gpt_key
    #load huggingface embedder or openai embedder
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    #embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    # cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    #     embedder, fs, namespace='all-MiniLM-L6-v2'
    # )

    
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
                                                    column_units=feature['metadata']['unit'] if 'unit' in feature['metadata'] else '',
                                                    column_concept=feature['metadata']['concept'] if 'concept' in feature['metadata'] else '',
                                                    column_column_stats= ', '.join(f'{k}={v}' for k, v in feature['metadata']['column_stats'].items()))
                metadata={'name':feature['name'],'object_id':object_info['id'],'object_type':obj['type']}
                groundings_info=fetch_groundings(list(feature['metadata']['groundings']['identifiers'].keys())) #fetch one at a time??
                if 'error' != groundings_info:
                    if 'grounding' in feature.keys() and len(list(feature['grounding']['identifiers'].keys()))>0 :
                        grounding_info = fetch_groundings(list(feature['grounding']['identifiers'].keys()))
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
    os.makedirs(db_dir,exist_ok=True)
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder) #load
    vectorstore.add_texts(texts=text_chunks,metadatas=metadatas)
    
    return vectorstore

def short_feature_embed(objects:List[Dict],db_dir="./chroma_db"): #dataset)
    """
    Takes a list of objects (models or datasets) and their object type in a dict format and embeds their features in the vector store
    Inputs:
        objects: List[Dict] = List of objects to be embedded in format -  [{'info':object_dict,'type':'model' or 'dataset'}]
    Outputs:
        retriever - langchain retriever object
    
    Example usage:
        vs=embed([{"info":example_model_get},'type':'model'])
    This embedder only embeds features based on their information (name only)
    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    import os
    from keys import gpt_key
    #load huggingface embedder or openai embedder
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    #embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    # cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    #     embedder, fs, namespace='all-MiniLM-L6-v2'
    # )
    
    text_chunks=[] #build text chunks
    metadatas=[] #build metadatas
    for obj in objects:
        object_info=obj['info']
        if obj['type']=='dataset':
            #create chunks in parallel
            for feature in object_info['columns']:
                text_chunk=""
                text_chunk+='Name:'
                text_chunk+=feature['name']
                text_chunk+='\nDescription:'
                text_chunk+=feature['description']
                print(f"Feature {feature['name']} on model {object_info['name']} was embedded")
                metadata={'name':feature['name'],'object_id':object_info['id'],'object_type':obj['type']}
                text_chunks.append(text_chunk)
                metadatas.append(metadata)
        elif obj['type'] == 'model': 
            for feature in object_info['model']['states']:
                text_chunk=""
                text_chunk+='Name:'
                text_chunk+=feature['name']
                print(f"Feature {feature['name']} on model {object_info['name']} was embedded")
                metadata={'name':feature['name'],'object_id':object_info['id'],'object_type':obj['type']}
                text_chunks.append(text_chunk)
                metadatas.append(metadata)
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder) #load
    vectorstore.add_texts(texts=text_chunks,metadatas=metadatas)
    
    return vectorstore

def document_embed(objects:List[Dict],db_dir="./chroma_db"):       
    """
    Create a text chunk represening each document (model, dataset)
    for use later in matching datasets and models

    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    import os
    from keys import gpt_key
    #load huggingface embedder or openai embedder
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    #embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    # cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    #     embedder, fs, namespace='all-MiniLM-L6-v2'
    # )
    
    text_chunks=[] #build text chunks
    metadatas=[] #build metadatas
    for obj in objects:
        object_info=obj['info']
        if obj['type']=='dataset':
            template="""\
            dataset name: {obj_name}
            dataset description: {obj_description}
            """
            text_chunk=template.format(obj_name=object_info['name'],
                                       obj_description=object_info['description'])
            # feature_template="""
            # feature name: {column_name}
            # feature description: {column_description}
            # data_type: {column_data_type}
            # feature unit type: {column_units}
            # feature numerical stats:  {column_column_stats}
            # feature concept : {column_concept}
            # """
            # for feature in 
        elif obj['type'] == 'model':
            template="""\
            model name: {obj_name}
            model description: {obj_description}
            """
            text_chunk=template.format(obj_name=object_info['name'],
                                       obj_description=object_info['description'])
            
        metadata={'name':object_info['name'],'object_id':object_info['id'],'object_type':obj['type']}
        text_chunks.append(text_chunk)
        metadatas.append(metadata)
        
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder) #load
    vectorstore.add_texts(texts=text_chunks,metadatas=metadatas)
    
    return vectorstore