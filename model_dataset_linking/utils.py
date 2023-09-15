# -*- coding: utf-8 -*-

from langchain.vectorstores import Chroma
DEFAULT_K = 5
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
from langchain.docstore.document import Document
from langchain.vectorstores.chroma import _results_to_docs_and_scores
from langchain.utils import xor_args

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