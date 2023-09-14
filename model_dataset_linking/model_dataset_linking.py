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
# to do: add other retrieval options (like dkg hops)
# to do: try different embedders or similarity search params (is another embedder better at passage level embedding?)
# to do: parallelize
# to do: llm and semantic short working decently in one to one, 

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
             'name':feature[0].metadata['name'],
             'score':feature[1]} for feature in ranked_list]
def prettify_documents(ranked_list):
    """takes a list of tuples of (document:Document, score:float), gets some 
    information and puts it into a format for response"""
    
    return [rank[0].metadata['object_id'] for rank in ranked_list]

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

def prettify_openai(output,k,dataset_id):
    # for this to work the openai output needs to be well defined... may need to change prompt
    import re
    pattern = r'\d+\.\s+'
    sections = re.split(pattern, output)
    sections = [section for section in sections[1:] if section.strip()]
    feature_names = [feature.split('Description')[0].rstrip() for feature in sections]
    ranked_list = [{'dataset_id':dataset_id,'feature_name':feature_name} for feature_name in feature_names]
    return ranked_list

def find_dataset_semantic_matching(model_id,dataset_ids=None,db_dir="./chroma_db"):
    """
    Match model to dataset by looking at the cosine similarity 
    between embeddings of model text chunks and dataset text chunks
    
    Model ID is a string that will be used to find the model embedding. 
    The model id should be the same as in the tds database and metadata in the vectorstore 
    If the model embedding doesn't exist we will embed it
    
    If a feature name is listed only get the dataset features for that feature 
    in the model, we will return ranked lists for each feature in the model
    
    Datasets is a list of dataset ids. These ids are used to filter the dataset of embeddings.
    If dataset ids is None then try all datasets.
    
    Returns a dictonary of ranked lists with each key being a feature name requested. 
    Note that for the scores listed in the ranked lists higher is worse.
    
    Example Usage: 
        #all dataset case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id')
        #few datasets case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id',dataset_ids=['0fe1cf32-305d-41fa-8810-3647c9031d45','de6be6cb-b9a0-4959-b5c6-3745576adfc3','6d8cab47-e206-4b50-a745-2bda112d0892'])
        
    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.storage import LocalFileStore
    from keys import gpt_key
    
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder)
    filter_terms={"$and":[{"object_type": {
        "$eq": 'model'
    }},{"object_id": {
        "$eq": model_id
    }}]}
    model_embed=vectorstore.get(where=filter_terms,include=['embeddings', 'documents', 'metadatas'])['embeddings']  
    if dataset_ids==None:
        filter_terms={"object_type": {
            "$eq": 'dataset'
        }}
        
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
                
    top_k_dataset_features=vectorstore.similarity_search_by_vector_with_score(model_embed, filter=filter_terms,k=5)
    pretty_result = prettify_documents(top_k_dataset_features)
    return pretty_result
    
#main endpoint candidate    
def find_dataset_features_basic_llm_query_1(model_id,feature_name=None,dataset_ids=None,db_dir="./chroma_db"):
    """
    Match model to features in given datasets by asking an llm to rank the features.
    Note this only does feature to feature matching for the moment.
    
    Model ID is a string that will be used to find the model embedding. 
    The model id should be the same as in the tds database and metadata in the vectorstore 
    If the model embedding doesn't exist we will embed it
    
    If a feature name is listed only get the dataset features for that feature 
    in the model, we will return ranked lists for each feature in the model
    
    Datasets is a list of dataset ids. These ids are used to filter the dataset of embeddings.
    If dataset ids is None then try all datasets.
    
    Returns a dictonary of ranked lists with each key being a feature name requested. 
    
    Example Usage: 
        #all dataset case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id')
        #few datasets case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id',dataset_ids=['0fe1cf32-305d-41fa-8810-3647c9031d45','de6be6cb-b9a0-4959-b5c6-3745576adfc3','6d8cab47-e206-4b50-a745-2bda112d0892'])
        # for a specific feature
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id',feature_name='S')
        
    """
    from langchain import PromptTemplate
    #save $$ in dev
    from langchain.cache import SQLiteCache
    from langchain import OpenAI
    import langchain
    from langchain.chains import LLMChain
    from keys import gpt_key
    
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.document_loaders import TextLoader
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    langchain.llm_cache = SQLiteCache(database_path=".langchain.db")
    prompt="""""Here are a list of epidemiology dataset features with their names and descriptions.
        Please rank in order from most similar to least similar, the dataset features to an epidemiology 
        feature with the name {model_feature_name} and give a rationale for each dataset feature as to why you ranked it where you did.
        
        Dataset features list :
            {dataset_features_list}"""
    prompt_2="""Here are a list of epidemiology dataset features with their names and descriptions.
        Please rank in order from most similar to least similar, the dataset features to an epidemiology 
        feature with the name {model_feature_name} and give a rationale for each dataset feature as to why you ranked it where you did.
        
        Please give your answer in the following format - 
        1. [Dataset Feature Name of highest ranked feature]
        Rationale:[rationale for ranking of highest ranked feature]
        2.[Dataset Feature Name of second highest ranked feature]
        Rationale:[rationale for ranking of second highest ranked feature]
        etc... for all of the dataset features
        
        Dataset features list :
            {dataset_features_list}
        """
    #to do: modify prompt based on k in top k
    prompt_3="""Here are a list of epidemiology dataset features with their names and descriptions.
        Please rank in order from most similar to least similar, the dataset features to an epidemiology 
        feature with the name {model_feature_name}.
        
        Output your ranking list in the following format:
            1. [dataset_feature_name]
            2. [dataset_feature_name]
            3. [dataset_feature_name]
            4. [dataset_feature_name]
            5. [dataset_feature_name]

        Dataset features list :
            {dataset_features_list}"""
    #even the short prompt takes a bit of time, but could probably do them all
    #in parallel or if it is too slow we could use to generate our ground truth and curate manually from there...       
    prompt=PromptTemplate.from_template(prompt_3)
    #llm=OpenAI(model_name='gpt-3.5-turbo', temperature=0,openai_api_key=gpt_key)
    llm=OpenAI(model_name='gpt-4', temperature=0,openai_api_key=gpt_key)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder)
    model_info=get_model_info(model_id)
    model_embeds=vectorstore.get(where={'object_id':model_id})
    if len(model_embeds['ids'])==0:short_feature_embed([{'info':model_info,'type':'model'}]) #if model is not embedded, embed it now.
    results={}
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
        #feature_doc = vectorstore.get(where=filter_terms,include=['documents', 'metadatas'])['documents']
        #find matches in vector store using object_ids filter
        if dataset_ids==None:
            filter_terms={"object_type": {
                "$eq": 'dataset'
            }}
            
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
        #need to prefilter, make chain?
        top_k_dataset_features=chain.run(model_feature_name=feature['name'],dataset_features_list='\n'.join(vectorstore.get(where=filter_terms)['documents']))
        #post process pretty result
        pretty_result = prettify_openai(top_k_dataset_features,k=5,dataset_id='41a32771-7a35-4da5-98a6-d420172108e8') #replace with output parser? #output parser is probably fragile
        results[feature['name']]=pretty_result
        
    return results
    
#main endpoint candidate
def find_dataset_features_semantic_matching(model_id,feature_name=None,dataset_ids=None,db_dir="./chroma_db"):
    """
    Match model to features in given datasets by looking at the cosine similarity 
    between embeddings of model feature text chunks and dataset feature text chunks
    
    Model ID is a string that will be used to find the model embedding. 
    The model id should be the same as in the tds database and metadata in the vectorstore 
    If the model embedding doesn't exist we will embed it
    
    If a feature name is listed only get the dataset features for that feature 
    in the model, we will return ranked lists for each feature in the model
    
    Datasets is a list of dataset ids. These ids are used to filter the dataset of embeddings.
    If dataset ids is None then try all datasets.
    
    Returns a dictonary of ranked lists with each key being a feature name requested. 
    Note that for the scores listed in the ranked lists higher is worse.
    
    Example Usage: 
        #all dataset case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id')
        #few datasets case - 
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id',dataset_ids=['0fe1cf32-305d-41fa-8810-3647c9031d45','de6be6cb-b9a0-4959-b5c6-3745576adfc3','6d8cab47-e206-4b50-a745-2bda112d0892'])
        # for a specific feature
        dataset_features=find_dataset_features_semantic_matching('biomd0000000249-model-id',feature_name='S')
        
    """
    from langchain.embeddings import OpenAIEmbeddings,CacheBackedEmbeddings
    from langchain.storage import LocalFileStore
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    from keys import gpt_key
    
    #load vector store - 
    fs = LocalFileStore("./cache/")
    embedder=OpenAIEmbeddings(openai_api_key=gpt_key)
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embedder, fs, namespace='openai'
    )
    #embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    # cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    #     embedder, fs, namespace='all-MiniLM-L6-v2'
    # )
    
    vectorstore=ChromaPlus(persist_directory=db_dir, embedding_function=cached_embedder)
    model_info=get_model_info(model_id)
    model_embeds=vectorstore.get(where={'object_id':model_id})
    if len(model_embeds['ids'])==0:long_feature_embed([{'info':model_info,'type':'model'}]) #if model is not embedded, embed it now.
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
  
#second endpoint?
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
    
def evaluate_on_feature_finding_eval_dataset(eval_dataset,db_dir="./eval_dataset_chroma_db"):
    import os
    os.makedirs(db_dir,exist_ok=True)
    #vs=long_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    #vs=short_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    evaluation_scores=[]
    for model in eval_dataset['models']:
        #pred_ranking=find_dataset_features_semantic_matching(model['info']['id'],db_dir=db_dir)
        pred_ranking=find_dataset_features_basic_llm_query_1(model['info']['id'],db_dir=db_dir)
        gt_ranking=[d for d in eval_dataset['ground_truth'] if d["model_id"] == model['info']['id']][0]['ranking_lists']
        scores=get_feature_ranking_metrics(pred_ranking,gt_ranking)
        evaluation_scores.append({'model_id':model['info']['id'],'scores':scores,'pred':pred_ranking,'gt':gt_ranking})
        
    return evaluation_scores

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
    
def evaluate_on_dataset_finding_eval_dataset(eval_dataset,db_dir="./eval_dataset_chroma_db"):
    import os
    os.makedirs(db_dir,exist_ok=True)
    #vs=long_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    #vs=short_feature_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    vs=document_embed(eval_dataset['datasets']+eval_dataset['models'],db_dir=db_dir)
    evaluation_scores=[]
    for model in eval_dataset['models']:
        #pred_ranking=find_dataset_features_semantic_matching(model['info']['id'],db_dir=db_dir)
        pred_ranking=find_dataset_semantic_matching(model['info']['id'],db_dir=db_dir)
        gt_ranking=[d for d in eval_dataset['ground_truth'] if d["model_id"] == model['info']['id']][0]['ranking_lists']
        scores=get_dataset_ranking_metrics(pred_ranking,gt_ranking)
        evaluation_scores.append({'model_id':model['info']['id'],'scores':scores,'pred':pred_ranking,'gt':gt_ranking})
        
    return evaluation_scores
    
    