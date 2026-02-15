# Design document

## Objectives
- working prototype app
- grounded answers in KB
- answers must have citations
- If the KB doesn’t contain the answer, respond with: **“I can’t find this in the knowledge base”** and ask a clarifying question.

## Solution Design

- three components: data pipeline, backend, frontend

### Data pipeline

Generally, we use
- vector DB (in our case for simplicity vector plugin of sqlite) to store and chunks of the documents
- relational DB for analytical workload (we would have many reads on BE and ocassional write during data pipeline)
The pipeline would be composed of two steps:
- processing of documents in (data/raw/kb)
- processing of structured and semi-structured data

Processing of documents:
- chunk the markdown files according to markdown structure (leverage titles/subtitles/..)
- preprocess the chunk text for embedding (remove special characters) and for full text search (tokenize, remove whitespace, remove special characters, lemmatize, ..)
- embed the chunks using embedding model and full text for BM25 (here do typical cleaning such as tokenization / lemmatization)
- document name, section header, date etc stored as metadata
- each folder is separate index (metadata to filter on)
- we would store both retrieval_chunk and generation_chunk -- we give surrounding context to LLM to generate with
- for such small data we would use bruteforce "index", no need for ANN
- could be further on improved in many aspect according to experiments (evaluation) with things such as adding global context to chunks, ..

Processing of structured and semi-structured data:
- we would parse the kpi_catalog.csv and directory and store them as two separate tables in SQL DB

### Backend
- agent written in PydanticAI framework, FastAPI bakcned
- two tools, one to look up data in SQL DB and second one to search KB
- retrieval tool is standard pipeline of embedding -> search -> reranker
- prompt forces to LLM to say it doesnt know
- prompt forces LLM to check date of information per chunks and prefer authoritative/newer ones. (Could be also partially done programatically to let LLM know)
- include citations on output

Additional features later on
- store chat history in transactional DB
- summarize long conversations and store in transactional DB
- extract user preferences and store them in transactional DB. Keep in mind sometimes it might be better for user to explicitly specify preferences than to extract them on our own
- use observability tool

### Frontend
- simple prototype in chainlit (Python lib), later on in Typescript+React
- simple chat UI, ability to view citations etc
- later on ability to give feedback
