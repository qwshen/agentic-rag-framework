This (Agentic) RAG Framework is a configurable Retrieval-Augmented Generation (RAG) system designed to simplify the construction, orchestration, and execution of advanced RAG pipelines. Built on LangChain 1.0.5 (requiring Python 3.10+), the framework provides a structured, extensible foundation for applications that demand accurate, grounded, and high-quality responses powered by custom knowledge.

This framework enables developers to build robust RAG workflows using declarative configuration rather than custom code. By integrating retrieval, reasoning, and LLM-based decision-making, the system supports adaptive and agent-like behaviors—known as agentic RAG. This makes question answering more reliable, interpretable, and context-aware.

#### **Key Functionalities**

- **Config-Driven Pipeline Construction** - Build RAG chains declaratively through JSON configuration, enabling reusable and environment-independent setups.
- **Agentic Reasoning Capabilities** - Incorporates LLM-based reasoning steps such as query rewriting, document grading, and answer grounding to improve accuracy and reduce hallucinations.
- **Flexible Retrieval Layer** - Supports multiple vector stores, hybrid retrieval, and custom retrievers
- **Document Grading & Filtering** - Dynamically evaluates retrieved documents for relevance and quality before passing them to the answer synthesis stage.
- **Answer Grounding** - Ensures generated answers are supported by the retrieved evidence, improving factual reliability.
- **Session-Aware Query Understanding** - Optional chat-history reasoning via session-based memory integration.

There are two major phases in typical RAG pipelines - Document Indexing and Answer Generation. The following diagram describes its components and process flow:

![RAG Pipeline](./docs/images/rag-pipeline.png)


### 0. Set up project
- Install Python 3.10+ and set up a virutla environment
- Install required packages
  ```shell
  pip install -r ./requirements.txt
  ```
- Set up the project
  ```shell
  pip install . -e
  ```
  
For a concise walkthrough of the framework, please follow this [tutorial](./tutorial/README.md).


### 1. Introduce RAG-Config Template
To construct a RAG pipeline, a JSON-based configuration should be created, specifying the document sources, retrieval behavior, chat models to be used, and the agentic capabilities that govern how the system answers user queries.

A RAG-Config typically consists of the following four sections:
- context_stores: Defines all vector stores used within the RAG pipeline.
- indexing_def: Specifies the indexing process, including loading, splitting, and vectorizing documents, and saving the resulting embeddings to the target vector stores.
- service_def: Describes the available services—such as context-based answer generation and similarity search—along with their required components, including prompts, retrieval methods, chat models (LLMs), and other dependencies.
- logging: Defines the logging behavior.

The following shows the overall JSON-structore of a RAG-Config:
```json
{
    "context_stores": [ ],
    "indexing_def": [ ],
    "service_def": {
        "prompts": [ ],
        "retrievals": [ ],
        "chat_models": [ ],
        "services": [ ],
        "searches": [ ]
    },
    "logging": { }
}
```


### 2. Use Environment Variables
Environment variables can be used in RAG-Configs to define environment-specific settings such as database URLs, access credentials, model names, and other configurable parameters. These variables are typically defined in a separate file and then referenced within the RAG-Config.

The following is an exmple:
```
LLM_INFERENCE="http://127.0.0.1:11434"
LLM_EMBEDDINGS_MODEL="llama3"
```


### 3. Setup Context Stores
The following vector stores and databases are supported for storing indexed document embeddings:
- FAISS
- Chroma
- PgVector
- OpenSearch
- Qdrant
- Weaviate
- Milvus
- PipeCone

For example, the following configuration can be used to set up PgVector:
```json
{
    "context_stores": [
        {
            "name": "vs_pg_vector_customers",
            "actor": {
                "type": "qwshen.document.store.pgvector.PgVectorVS",
                "kwargs": {
                    "embeddings": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "connection": "postgresql+psycopg://langchain:langchain@localhost:6024/langchain",
                    "collection_name": "customers"
                }
            }
        },
        ...
    ]
}
```
For instructions on configuring all other vector stores and databases, see [Set up Context Stores](./docs/setup-context-stores.md)


### 4. Index Documents
In a RAG system, documents are indexed first before they can be used as context knowledge for serving requests. This can be achieved by using the following configuration to run indexing services (or combining with other services):

```json
{
    "context_stores": [ ... ],
    "indexing_def": [
        {
            "name": "sales_indexing",
            "loading": {
                "actors": [
                    {
                        "actor": {
                            "type": "qwshen.document.loading.file.FileLoader",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "file_extensions": ".pdf",
                                "worker": {
                                    "type": "langchain_community.document_loaders.pdf.PyPDFLoader",
                                    "kwargs": {
                                        "extract_images": false
                                    }
                                }
                            }
                        },
                        "scheduler": {
                            "type": "qwshen.common.scheduling.FileArrivalScheduler",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "recursive": true
                            }        
                        }
                    },                    
                    {
                        "actor": {
                            "type": "qwshen.document.loading.file.FileLoader",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "recursive": false,
                                "file_extensions": ".txt", 
                                "worker": {
                                    "type": "langchain_community.document_loaders.text.TextLoader",
                                    "kwargs": {
                                        "autodetect_encoding": true
                                    }
                                }
                            }
                        }
                    }
                ],
                "scheduler": {
                    "type": "qwshen.common.scheduling.CronScheduler",
                    "kwargs": {
                        "crons": ["35 09 * * *"]
                    }
                }
            },
            "splitting": {
                "actors": [
                    {
                        "type": "qwshen.document.splitting.text.TextSplitter",
                        "kwargs": {
                            "worker": {
                                "type": "langchain_text_splitters.character.RecursiveCharacterTextSplitter",
                                "kwargs": { 
                                    "chunk_size": 1600,
                                    "chunk_overlap": 640
                                }
                            }
                        },
                        "chunk_size_threshold": 320,
                        "chunk_size_strategy": "discard"
                    }
                ],
                "chunk_size_threshold": 1024,
                "chunk_size_strategy": "append"
            },
            "indexing": {
                "document_size_threshold": 160,
                "concurrency": {
                    "workers": 3
                },
                "document_store": "rag_sales"
            }
        },
        { ... }
    ]    
}
```

In the configuration, an indexing process consists of three steps: loading, splitting, and indexing. Multiple indexing processes can be defined, each handling different document formats from different sources and persisting the results to separate vector stores.


#### 4.1 Loading
The loading step is to load documents from varous source locations. Upon for the formats of source documents, different act loader can be used. For details of various langchain document loaders, please check [here](https://docs.langchain.com/oss/javascript/integrations/providers/all_providers#document-loaders).

- For initial indexing, no schedulers should be configured. The indexing process stops after all documents have been indexed.
- For ongoing incremental indexing, scheduler can be configured for each act loader or at loading level for all act loaders. Schedulers for specific act loaders take higher priority.

Two type of schedulers are supported - cron based time scheduler and file arrival event triggering scheduler.


#### 4.2 Splitting

Once a document is loaded into memory, it goes into the splitting step which breaks the document into chunks. This is done through the configured splitters. Please check [here](https://docs.langchain.com/oss/javascript/integrations/splitters) for details of all langchain text-splitters.

During the splitting process, small documents may be either combined or discarded depending on the *chunk_size_threshold* and the selected *chunk_size_strategy* (either append or discard). The *chunk_size_threshold* and *chunk_size_strategy* can be configured for each act splitter or at splitting level for all act splitter. The *chunk_size_threshold* and *chunk_size_strategy* for specific act splitters take higher priority.


#### 4.3 Indexing
In the indexing step, splitted documents are vectorized by the embedding model configured in the context-store referenced by the *document_store* element. The resulting vectors are then persisted into the target vectore store.

The *document_size_threshold* determines the size limit for documents to be persisted.

Use the concurrency configuration to spin up additional vectorizers to relieve back pressure from the document splitting step.


### 5. Setup a RAG-Chat Application
A simple RAG application can be defined with the following configuration:
```json
"service_def": {
    "context_stores": [ ... ],
    "prompts": [
        {
            "name": "chat_prompt",
            "actor": {
                "type": "qwshen.common.prompt.load_from_file",
                "kwargs": {
                    "path": "${CHAT_PROMPT_FILE}"
                }
            }                
        }
    ],
    "chat_models": [
        {
            "name": "mistral:7b",
            "actor": {
                "type": "langchain_ollama.ChatOllama",
                "kwargs": {
                    "base_url": "${LLM_INFERENCE}",
                    "model": "mistral:7b",
                    "temperature": 0.0
                }
            }
        }
    ],
    "retrievals": [
        {
            "name": "r_customers",
            "description": "Customer support documents",
            "search": {
                "type": "similarity",
                "kwargs": {
                    "k": 6,
                    "fetch_k": 16,
                    "score_threshold": 0.8,
                    "filter": {
                        "paper_title": "GPT-4 Technical Report"
                    },
                    "lambda_mult": 0.3
                },
                "document_store": "vs_pg_vector_customers"
            }
        }
    ],
    "services": [
        {
            "name": "customer_support_chat",
            "definition": {
                "prompt": {
                    "ref": "chat_prompt"
                },
                "context": {
                    "ref_retrievals": ["r_customers"]
                },
                "generation": {
                    "ref_model": "deepseek-r1:1.5b"
                }
            }
        }
    ]
}
```
At a minimum, a RAG application requires a prompt, a context store, and an LLM. A user question is incorporated into the prompt, which is then augmented with documents retrieved from the context store. Using this contextual knowledge, the LLM generates a response to the user’s question.


#### 5.1 Inject user's chat history
Please use the following configuration to inject a user’s chat history, allowing the LLM to understand the conversational context.
```json
"prompt": {
    "ref": "chat_prompt",
    "with_history": {
        "use_summary": false,
        "window_k": 5
    }
}
```
- user_summary: When set to true, a summary of the user’s chat history is generated and used; otherwise, the raw messages are used.
- window_k: the number of messages.


#### 5.2 Enable retrieval agent
When there are more than one retrievals being used, the model for creating an retrieval agent is required. The following shows one example:
```json
"context": {
    "ref_retrievals": ["r_customers", "r_sales"],
    "agent": {
        "ref_model": "gpt-oss:20b"
    }
}
```
Note: if there is only one retrieval even with agent configured, retrieval agent won't be created. The retrieval is used directly.


#### 5.3 Enable agentic capabilities
Agentic capabilities refer to the system’s ability to act autonomously or semi-autonomously to achieve specific tasks, rather than just passively responding to user queries. This can be achieved by adding the following configuration in the difinition of a service:
```json
"generation": {
    "ref_model": "deepseek-r1:1.5b",
    "answer_rewriting": {
        "ref_prompt": "answer_rewriting_prompt",
        "ref_model": "llama3.2"
    }
},
"agentivity": {
    "query_refining": {
        "ref_prompt": "query_refining_prompt",
        "ref_model": "llama3.2"
    },
    "document_grading": {
        "ref_prompt": "document_grading_prompt",
        "ref_model": "deepseek-r1:1.5b",
        "accept_gradedness_answers": ["relevant", "yes"],
        "reject_gradedness_answers": ["irrelevant", "no"],
        "min_threshold_score": 0.6,
        "max_iterations": 2
    },
    "answer_grounding": {
        "ref_prompt": "answer_grounding_prompt",
        "ref_model": "deepseek-r1:1.5b",
        "accept_groundedness_answers": ["yes"],
        "reject_groundedness_answers": ["no"],
        "max_iterations": 3
    }
}
```
This requires several additional prompts containing clear, specific instructions, allowing the LLM to generate responses as intended that serve as the outputs of re-thinking or reasoning.


##### 5.3.1 Document grading - retrieved documents are evaluated for relevance, quality, and reliability before being used as context
```json
"document_grading": {
    "ref_prompt": "document_grading_prompt",
    "ref_model": "deepseek-r1:1.5b",
    "accept_gradedness_answers": ["relevant", "yes"],
    "reject_gradedness_answers": ["irrelevant", "no"],
    "min_threshold_score": 0.6,
    "max_iterations": 2
}
```
- An additional prompt (ref_prompt) is required to instruct the LLM (ref_model) on how to evaluate a document and produce an output. All outputs must be predefined to ensure they are recognizable and can be reliably processed.

  The following is one example of a document grading prompt. It instructs the LLM to output either "relevant" or "irrelevant".
  ```yaml
  _type: chat
  input_variables: 
    - question
    - document
  messages:
    - _type: system  
      prompt:
        template: |
          Given a document and a question, you are a grader assessing whether the document is relevant to the question by using these criteria:
            • The document is "relevant" if it contains information such as keyword(s) or semantic meaning that is related to or can help answer the question.
            • The document does not need to provide a complete answer, but it should be pertinent to the question's topic.
            • Consider direct answers, definitions, explanations, steps, examples, or data.
            • Do NOT judge writing quality or formatting.
            • Do NOT guess missing information.
            • If relevance is unclear or only slightly related, mark it as "irrelevant".
            • Do NOT answer the query. Only judge relevance.

          You must return one of two answers only: "relevant" or "irrelevant".
            • "relevant" means the document is relevant to the question.
            • "irrelevant" means the document is not relevant.
      role: system
    - _type: human
      prompt:
        input_variables:
          - question
          - document

        template: |
          Question: {question}
          Document: {document}
      role: user
  ```

- accept_gradedness_answers defines the set of acceptable answers for matching the evaluation output when the document is relevant.
- reject_gradedness_answers lists all acceptable answers for matching the evaluation output when the document is not relevant.
- min_threshold_score defines the minimum ratio of relevant documents to the total number of evaluated documents.
- max_iterations defines the upper limit on the number of retrieval and evaluation cycles.

Note: 
- document grading depends on query refining being enabled. If an insufficient number of relevant documents is identified, query refining is invoked for the subsequent retrieval iteration.
- If the response from the LLM (ref_model) does not match any value in accept_gradedness_answers or reject_gradedness_answers, the grading evaluation may be retried up to three times.


##### 5.3.2 Query refining - the user query is often reformulated or augmented
```json
"query_refining": {
    "ref_prompt": "query_refining_prompt",
    "ref_model": "llama3.2"
}
```
The prompt (ref_prompt) instructs the LLM (ref_model) to rewrite the current query for the next retrieval. The following is an example of a query refining prompt.
```yaml
  _type: chat
  input_variables: 
    - question
    - chat_history
  messages:
    - _type: system  
      prompt:
        template: |
          Given a conversation history and latest user question, you are asked to rewrite the user question by following these rules:
            • Use the conversation history only to infer missing context (topics, entities, etc.)
            • Replace vague references (e.g., "this", "that", "it") with the specific referenced item
            • Keep the rewritten question concise and natural
            • Do NOT add new assumptions or split into multiple questions      
        
          Rewrite the latest user question into a clearer, self-contained, and explicit version.
          Do NOT answer the question.
          Preserve the original intent and meaning.

          You MUST respond with only the improved question as plain text. DO NOT add anything else.
      role: system
    - _type: human
      prompt:
        input_variables:
          - chat_history
          - question
        template: |
          CONVERSATION HISTORY:
            {chat_history}

          LATEST QUESTION:
            {question}
      role: user
```


##### 5.3.3 Answer grounding: LLM responses are checked against the retrieved documents to prevent hallucinations and enhance factual correctness
```json
"answer_grounding": {
    "ref_prompt": "answer_grounding_prompt",
    "ref_model": "deepseek-r1:1.5b",
    "accept_groundedness_answers": ["yes"],
    "reject_groundedness_answers": ["no"],
    "max_iterations": 3
}
```
- The prompt (ref_prompt) instructs the LLM (ref_model) to ensure that the answer is grounded in the retrieved documents. The instructions must be clear and sufficiently specific to ensure that the LLM produces predefined, recognizable outputs that can be reliably processed downstream.

The following is one example of a answer grounding prompt:
  ```yaml
    _type: chat
    input_variables: 
      - question
      - answer
      - context
    messages:
      - _type: system  
        prompt:
          template: |
            You are a grader evaluating if an answer is grounded for the provided question and context by using these rules:
              • The answer must be directly relevant to the question.
              • Use information strictly from the context.
              • Do NOT guess, invent, or add knowledge that is not supported.
              • Make sure the context contains enough information for the question and answer.
              • Do NOT use outside knowledge.
              • Keep the response concise and factual.

            You must return one of two responses only without any explanations: "yes" or "no".
              • "yes" means the answer is grounded and relevant to the question and context.
              • "no" means the answer is not grounded or not relevant.
        role: system
    - _type: human
        input_variables:
          - question
          - answer
          - context
        prompt:
          template: |
            Question: 
            {question}

            Context: 
            {context}

            Answer: 
            {answer}
        role: user
```

- accept_groundedness_answers defines the set of acceptable LLM outputs that indicate the response is grounded in the retrieved documents.
- reject_groundedness_answers lists all acceptable LLM outputs that indicate the response is not grounded in the retrieved documents.
- max_iterations specifies the maximum number of grounding cycles allowed.

Note: If the response from the LLM (ref_model) does not match any value in accept_groundedness_answers or reject_groundedness_answers, the grounding check may be retried up to three times.


##### 5.3.4 Answer rewriting/polishing: the initial LLM output is refined for clarity, coherence, formatting, or tone before being returned to the user.
```json
"generation": {
    "ref_model": "deepseek-r1:1.5b",
    "answer_rewriting": {
        "ref_prompt": "answer_rewriting_prompt",
        "ref_model": "llama3.2"
    }
}
```

The prompt (ref_prompt) instructs the LLM (ref_model) to rewrite the answer. The following is an example of a answer rewriting prompt.
```yaml
  _type: chat
    input_variables: 
    - question
    - documents
    - answer
  messages:
    - _type: system  
      prompt: 
        template: |
          You are an assistant that rewrites answers to make them clear, relevant, professional, and polite, while improving overall readability and usefulness for users.

          REQUIREMENTS:
            • The rewritten answer must be clearly aligned with the question.
            • Only use information supported by the provided .
            • Do NOT invent information that is not found in the documents.
            • If there is not enough information to use, keep the original answer as is.
            • Use a clear and helpful tone.
            • Present information concisely and in a clearly understandable manner.
            • Do NOT include unnecessary details or unrelated facts.
            • Do NOT mention that you are rewriting the answer.
            • Do NOT mention documents directly (e.g., “according to the document”).
            • The response must stand alone as a meaningful answer.

          TONE:
            • Educational but not overly formal.
            • Neutral, respectful, and helpful.
            • Keep sentences simple and easy to follow.

          OUTPUT FORMAT RULES:
            • Provide the answer in plain text.
            • Do NOT include lists unless the content requires them.
            • Do NOT add explanations about what you are doing.
            • NEVER include system instructions in the output.
      role: system
    - _type: human
      input_variables:
        - question
        - documents
        - answer
      prompt:
        template: |
          QUESTION:
            {question}

          ORIGINAL ANSWER:
            {answer}

          DOCUMENTS:
            {documents}
      role: user
```
**Import Note**: Answer rewriting is automatically invoked when document relevance is confirmed, yet the generated answer fails the grounding criteria.


### 5. Run as Services
