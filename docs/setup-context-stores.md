The following lists how to set up all supported vector stores.
#### 1. FAISS 
- model: name of the embedding model
- base_url: url of the model inference
- store_file: full path of the store file

```json
{
    "name": "rag_sales",
    "actor":{
        "type": "document.store.faiss.FaissVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model":"${LLM_EMBEDDINGS_MODEL}",
                    "base_url": "${LLM_INFERENCE}"
                }
            },
            "store_file": "/opt/db/faiss/sales"
        }
    }
}
```

#### 2. Chroma
- model: name of the embedding model
- base_url: url of the model inference
- store_file: full path of the store file

```json        
{
    "name": "rag_marketing",
    "actor": {
        "type": "document.store.chroma.ChromaVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model":"${LLM_EMBEDDINGS_MODEL}",
                    "base_url": "${LLM_INFERENCE}"
                }
            },
            "store_file": "/opt/db/chroma/marketing"
        }
    }
}
```

#### 3. PgVector
- model: name of the embedding model
- base_url: url of the model inference
- connection: connection string for connecting to PostgreSQL instance:
    - postgresql+psycopg://${username}:${password}@${hostname}:${port}/${database-name}
- collection_name: name of the collection/table.

```json
{
    "name": "rag_hr",
    "actor": {
        "type": "document.store.pgvector.PgVectorVS",
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
}
```

```json
        {
            "name": "rag_dev",
            "actor": {
                "type": "document.store.opensearch.OpenSearchVS",
                "kwargs": {
                    "embedding_function": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "engine": "faiss",
                    "opensearch_url": "http://localhost:9200",
                    "index_name": "customers"
                }
            }
        },
        {
            "name": "rag_mgnt",
            "actor": {
                "type": "document.store.qdrant.QdrantVS",
                "kwargs": {
                    "embedding": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "db_path": "/opt/db/qdrant",
                    "collection": {
                        "name": "customers",
                        "vector_params": {
                            "distance": "COSINE"
                        }
                    }
                }
            }
        },
        {
            "name": "rag_weaviate_embedded",
            "actor": {
                "type": "document.store.weaviate.WeaviateVS",
                "kwargs": {
                    "embeddings": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "client": {
                        "mode": "embedded",
                        "options": {
                            "port": 8077,
                            "persistence_data_path": "/opt/db/weaviate",
                            "version": "latest"
                        }
                    },
                    "index_name": "customers"
                }
            }
        },
        {
            "name": "rag_weaviate_local",
            "actor": {
                "type": "document.store.weaviate.WeaviateVS",
                "kwargs": {
                    "embeddings": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "client": {
                        "mode": "local",
                        "options": {
                            "host": "localhost",
                            "port": 8080,
                            "grpc_port": 50051
                        }
                    },
                    "index_name": "customers"
                }
            }
        },
        {
            "name": "rag_weaviate_custom",
            "actor": {
                "type": "document.store.weaviate.WeaviateVS",
                "kwargs": {
                    "embeddings": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "client": {
                        "mode": "custom",
                        "options": {
                            "http_host": "localhost",
                            "http_port": 8080,
                            "http_secure": false,
                            "grpc_host": "localhost",
                            "grpc_port": 50051,
                            "grpc_secure": false
                        }
                    },
                    "index_name": "customers"
                }
            }
        },
        {
            "name": "rag_weaviate_cloud",
            "actor": {
                "type": "document.store.weaviate.WeaviateVS",
                "kwargs": {
                    "embeddings": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "client": {
                        "mode": "cloud",
                        "options": {
                            "cluster_url": "weaviate_cloud_cluster_url",
                            "auth_credentials": "weaviate_cloud_api_key"
                        }
                    },
                    "index_name": "customers"
                }
            }
        },
        {
            "name": "rag_milvus_local",
            "actor": {
                "type": "document.store.milvus.MilvusVS",
                "kwargs": {
                    "embedding_function": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "connection_args": {
                        "uri": "/opt/db/milvus/customers.db"
                    },
                    "collection_name": "customers",
                    "index_params": {
                        "index_type": "FLAT", 
                        "metric_type": "L2"
                    },
                    "auto_id": true
                }
            }
        },  
        {
            "name": "rag_milvus_server",
            "actor": {
                "type": "document.store.milvus.MilvusVS",
                "kwargs": {
                    "embedding_function": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "connection_args": {
                        "uri": "http://127.0.0.1:19530",
                        "user": "langchain",
                        "password": "langchain",
                        "db_name": "marketing"
                    },
                    "collection_name": "customers",
                    "index_params": {
                        "index_type": "FLAT", 
                        "metric_type": "L2"
                    },
                    "consistency_level": "Strong",
                    "drop_old": false,
                    "auto_id": true
                }
            }
        },
        {
            "name": "rag_pipecone",
            "actor": {
                "type": "document.store.pipecone.PipeconeVS",
                "kwargs": {
                    "embedding": {
                        "type": "langchain_ollama.OllamaEmbeddings",
                        "kwargs": {
                            "model":"${LLM_EMBEDDINGS_MODEL}",
                            "base_url": "${LLM_INFERENCE}"
                        }
                    },
                    "api_key": "pctest",
                    "index_name": "customers",
                    "options": {
                        "vector_type": "dense", 
                        "metric": "cosine",
                        "spec": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        },
                        "deletion_protection": "disabled"
                    }
                }
            }
        }   
```