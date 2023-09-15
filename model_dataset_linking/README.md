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
- [ ] Add pre-filtering to llm prompt feature matching when number of features is large (performance erodes with large amount of features)
- [ ] Add top k arg to llm prompt method
- [X] write recursive get top k docs, then assess their features in a one to few manner.
- [ ] Generate a large and entirely synthetic dataset(s)
- [ ] Add evaluation options for generic datasets (kilt or make a subset..)
- [X] Add feature gt to one to many features
- [ ] implement method to treat model and features as one document and do qa over documents (llm-in-a-box approach) to find model features in the one model to many datasets case

## Ideas 

### Search vs Recommendations:
Is this a search problem or a recommendations problem? We want to find recommend 
dataset that will help the user complete their process faster -
we are doing this by looking for features and documents that are 
semantically similar but we could use user(s) info as well and user other factors
to rank relevance with the goal of reducing user search time

### Other Evaluation Methods/Datasets
Evaluating document retrieval on kilt with same metrics (prec@k,rec@k,em@k) is probably a good proxy.
Evaluation on question answering datasets would also be a good metric, 
maybe extract a subset with shorter answers or a make a similar wikipedia feature finding dataset?

### Current Challenges 
When model feature information is very short and non-descriptive and there are many similar datasets and dataset features
this problem becomes very much a needle in the haystack problem when the dataset amounts get large..

We don't get very descriptive model feature descriptions. If we or data 
annotation could use model source documents to create better model 
name/descriptions this would be alot easier. Maybe we could create essentially pseudo names given model code/other model info?

## Implementation 
For semantic matching we use langchain's implementation of openai embeddings, which we 
then save to chroma db. Chromadb by default compares two dense vectors using cosine 
similarity.

To prompt the llm per as described in methodology we use gpt-3.5-turbo or gpt-4 using langchain.

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
We evaluate on three primary metrics - 

precision at top k (of the top k results returned, how many are in the top k of the ground truth)
recall at top k (of the top k ground truth results how many are in the top k of the results returned)
exact match at top k (of the top k, how many of the rankings are an exact match between the ground truth and the results?)

We generally use k=(1,3,5) but we could set it equal to anything we like..

We have a few evaluation datasets at the moment for multiple use cases:

### one to one feature matching

Given one model and one dataset, can we properly rank the dataset features
against each model feature (SIR). 

We only have one dummy example - a covid cases dataset from the cdc and a sir model.

We should be able to enlarge this dataset using user/demo data.

This dataset can be found in eval_datasets/one_to_one_features.json

### one model to few matching

Given one model and a few datasets, can we properly rank the dataset features
against each model feature (SIR).

This dataset can be found in eval_datasets/one_to_few_features.json

### one to few documents  

Given one model and a few relevant datasets (5), can we properly rank the documents 
for relevance to the model? (top 3 for example)

We have one truly relevant document (metrics@3 matter most) and 2 less/irrelevant ones.

This dataset can be found in eval_datasets/one_to_few_datasets.json

### one to many documents  

Given one model and many datasets (10), can we properly rank the documents 
for relevance to the model?

We have one truly relevant document (metrics@1 matter most) and 9 less/irrelevant ones.

This dataset can be found in eval_datasets/one_to_many_datasets.json

### one to many features 
Given one model and many datasets(10), can we properly find dataset features
to match the model features.
 
We use a basic SIR model that is described as an SIR model for the U.S 
and one real document and 9 less/irrelevant ones.

This dataset can be found in eval_datasets/one_to_many_features.json


