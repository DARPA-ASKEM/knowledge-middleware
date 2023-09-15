# -*- coding: utf-8 -*-
"""
The file contains code to find relevant datasets for models and to find relevant
dataset features for a model feature.
"""

from utils import ChromaPlus,get_model_info
from embed import short_feature_embed,long_feature_embed,document_embed


def find_dataset_features_hierarchical(model_id,dataset_ids=None,dataset_db_dir="./chroma_db",features_db_dir="./chroma_db"):
    """
    Match features in a model to features of datasets in the given set of datasets.
    Do this byu first findng similar documents and then evaluating against those documents features.
    

    """
    relevant_docs=find_dataset_semantic_matching(model_id,dataset_ids=dataset_ids,db_dir=dataset_db_dir)
    features=find_dataset_features_semantic_matching(model_id,db_dir=features_db_dir,dataset_ids=relevant_docs)
    return features

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

def prettify(ranked_list):
    """takes a list of tuples of (document:Document, score:float), gets some 
    information and puts it into a format for response"""
    
    return [{'dataset_id':feature[0].metadata['object_id'],
             'feature_name':feature[0].metadata['name'],
             'score':feature[1]} for feature in ranked_list]
def prettify_documents(ranked_list):
    """takes a list of tuples of (document:Document, score:float), gets some 
    information and puts it into a format for response"""
    
    return [rank[0].metadata['object_id'] for rank in ranked_list]



def prettify_openai(output,k,dataset_id):
    # for this to work the openai output needs to be well defined... may need to change prompt
    import re
    pattern = r'\d+\.\s+'
    sections = re.split(pattern, output)
    sections = [section for section in sections[1:] if section.strip()]
    feature_names = [feature.split('Description')[0].rstrip() for feature in sections]
    ranked_list = [{'dataset_id':dataset_id,'feature_name':feature_name} for feature_name in feature_names]
    return ranked_list