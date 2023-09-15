# Model Dataset Linking
This directory contains code to retrieve semantically similar features from available datasets
given a model feature as well as semantically similar datasets given a model.

## Methodology
To match models to datasets we use a language model to create embeddings of the 
model's name and description and do a cosine similiarity search against available documents.

To match model features to dataset features we have multiple methods implemented for matching
as well as multiple use cases. 

First, the use case of when a user is trying to match a model feature to features 
in one or a few known datasets. This would occur on the workflow screen. 

In this case we have implemented methods to either embed the feature names and descriptions and compare cosine 
similiarity as above or another method where we take the features and feed them along with a 
query and some context to an LLM and ask the LLM to rank them in terms of similarity
to the model feature. On our current basic evaluation datasets the llm methods performs better but is slower.

Second, we have the use case that the user has a model and is trying to find 
relevant datasets and dataset features from the entire set of available datasets.

For the case that we are trying to recommend datasets we treat the problem as a semantic search problem
and embed the model name and description and compare it to the embedded dataset name and description.

This works reasonably well and we take a similar approach in other projects with much larger datasets
and retrieval works well there (on kilt - https://eval.ai/web/challenges/challenge-page/689/overview)

For the case that we want to find dataset features given one model feature and many 
datasets and dataset features we have implemented a method to first match the model to datasets
and then rank the features from those datasets against the model feature.

This works about as well as the one to few datasets method in the case where we the features 
we care about are only in a few datasets.

## To do
- [ ] add api format to functions
- [ ] add docker container
- [ ] add other retrieval options (like dkg hops)
- [ ] add more info from MIT apis
- [ ] try different embedders or similarity search params (is another embedder better at passage level embedding?)
- [ ] parallelize certain sections
- [ ] Add pre-filtering to llm prompt feature matching when number of features is large
- [ ] Add top k arg to llm prompt method
- [X] write recursive get top k docs, then assess their features in a one to few manner.
- [ ] Generate a large and entirely synthetic dataset(s)
- [ ] Add evaluation options for generic datasets (kilt or make a subset..)
- [ ] Add feature gt to 
- [ ] implement method to treat model and features as one document and do qa over documents (llm-in-a-box approach) to find model features in the one model to many datasets case

## Ideas 

Search vs Recommendations:
Is this a search problem or a recommendations problem? We want to find recommend 
dataset that will help the user complete their process faster -
we are doing this by looking for features and documents that are 
semantically similar but we could use user(s) info as well and user other factors
to rank relevance with the goal of reducing user search time

## Implementation 
For semantic matching we use langchain's implementation of openai embeddings, which we 
then save to chroma db. Chromadb by default compares two dense vectors using cosine 
similarity.

To prompt the llm per as described in methodology we use gpt-3.5-turbo using langchain.

## Installation
Setup a virtual env.
Then install requirements.
```
conda create -n model-dataset-matching python=3.9
conda activate model-dataset-matching
pip install -r requirements.txt
```

## Usage

To embed objects use code found in embed.
To find features use code found in find.
To evaluate use code in evaluate.
Example usage is in the description of each function.

## Evaluation

We have a few evaluation datasets at the moment for multiple use cases -

one to one - Given one model and one dataset, can we properly rank the dataset features
against each model feature (SIR)

one to few - Given one model and a few datasets, can we properly rank the dataset features
against each model feature (SIR)

one to many documents - Given one model and many datasets (10), can we properly 
rank the documents for relevance to the model?


