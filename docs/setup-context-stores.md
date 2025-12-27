The following lists how to set up all supported vector stores.
#### 1. FAISS 
- model: name of the embedding model
- base_url: url of the model inference
- store_file: full path of the store file

The following example shows how to use FAISS to persist sales documnets. The store file is located at /opt/db/faiss/sales. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

```json
{
    "name": "sales_vs",
    "actor":{
        "type": "document.store.faiss.FaissVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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

The following example shows how to use Chroma to persist marketing documnets. The store file is located at /opt/db/chroma/marketing. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

```json        
{
    "name": "marketing_vs",
    "actor": {
        "type": "document.store.chroma.ChromaVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "ollama3",
                    "base_url": "http://127.0.0.1:11434"
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

This following example shows how to use PgVector to persist human resources documents. The PostgreSQL instance with pgvector runs at 127.0.0.1:6024 and is accessed using the langchain user. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

```json
{
    "name": "hr_vs",
    "actor": {
        "type": "document.store.pgvector.PgVectorVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "ollama3",
                    "base_url": "http://127.0.0.1:11434"
                }
            },
            "connection": "postgresql+psycopg://langchain:langchain@localhost:6024/langchain",
            "collection_name": "hr"
        }
    }
}
```

Note: to set up and use a test local PgVector store, please run the following docker container:
```shell
docker pull pgvector/pgvector:pg16

docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
```  

#### 4. OpenSearch

The following example shows how to use OpenSearch to persist customer documents. The OpenSearch instance is hosted at http://127.0.0.1:9600 with faiss engine. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

```json
{
    "name": "customer_vs",
    "actor": {
        "type": "document.store.opensearch.OpenSearchVS",
        "kwargs": {
            "embedding_function": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "ollama3",
                    "base_url": "http://127.0.0.1:11434"
                }
            },
            "engine": "faiss",
            "opensearch_url": "http://127.0.0.1:9200",
            "index_name": "customers"
        }
    }
}
```

Note: to set up and use a test local OpenSearch store, please run the following docker container:

```
docker pull opensearchproject/opensearch:latest

docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" -e "plugins.security.disabled=true" -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=PwD4aDm@LoCAl" opensearchproject/opensearch:latest
```

To test if the server is up and running:
```
curl http://localhost:9200 -ku admin:PwD4aDm@LoCAl
```

To query data inside:
```
 curl -X GET http://localhost:9200/customers/_search?pretty -ku admin:PwD4aDm@LoCAl
 ```

#### 5. Qdrant

The following examples show how to use Qdrant to persist customer documents. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

##### 5.1 Local mode. The database file is located at /opt/db/qdrant. 

```json
{
    "name": "rag_mgnt",
    "actor": {
        "type": "document.store.qdrant.QdrantVS",
        "kwargs": {
            "embedding": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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
}
```

##### 5.2 Server mode. A Qdrant instance is set up at http://localhost:6333 with api key as "test-api-key".
```json
{
    "name": "rag_mgnt",
    "actor": {
        "type": "qwshen.document.store.qdrant.QdrantVS",
        "kwargs": {
            "embedding": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model":"${LLM_EMBEDDINGS_MODEL}",
                    "base_url": "${LLM_INFERENCE}"
                }
            },
            "db_server": {
                "url": "http://localhost:6333",
                "api_key": "test-api-key"
            },
            "collection": {
                "name": "customers",
                "vector_params": {
                    "distance": "COSINE"
                }
            }
        }
    }
}
```

#### 6. Weaviate

The following examples show how to use Weaviate to psersist customer documents in different deployment modes. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

##### 6.1 Embedded mode with data file being located at /opt/db/weaviate/customers.
```json
{
    "name": "rag_weaviate_embedded",
    "actor": {
        "type": "document.store.weaviate.WeaviateVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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
}
```

##### 6.2 Local mode (normally for development) - a local weaviate instance is running
```json
{
    "name": "rag_weaviate_local",
    "actor": {
        "type": "document.store.weaviate.WeaviateVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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
}
```

##### 6.3 Custom mode - a standalone weaviate server is running (remotely)
```json
{
    "name": "rag_weaviate_custom",
    "actor": {
        "type": "document.store.weaviate.WeaviateVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
                }
            },
            "client": {
                "mode": "custom",
                "options": {
                    "http_host": "192.168.0.100",
                    "http_port": 8080,
                    "http_secure": false,
                    "grpc_host": "192.168.0.100",
                    "grpc_port": 50051,
                    "grpc_secure": false
                }
            },
            "index_name": "customers"
        }
    }
}
```

##### 6.4 Cloud mode - weaviate service is running in cloud.
```json
{
    "name": "rag_weaviate_cloud",
    "actor": {
        "type": "document.store.weaviate.WeaviateVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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
```

#### 7. Milvus
The following examples show how to use Milvus to store customer documents in local and server modes. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.

##### 7.1 Local mode with data file in local storage.
```json
{
    "name": "rag_milvus_local",
    "actor": {
        "type": "document.store.milvus.MilvusVS",
        "kwargs": {
            "embedding_function": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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
}
```

##### 7.2 Server mode
```json
{
    "name": "rag_milvus_server",
    "actor": {
        "type": "document.store.milvus.MilvusVS",
        "kwargs": {
            "embedding_function": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
                }
            },
            "connection_args": {
                "uri": "http://192.168.0.100:19530",
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
}
```

#### 8. Pipecone
The following example shows how to use pipecore to store customer documents in pipecone cloud environment. Embeddings are generated using the Llama 3 model served by Ollama at http://127.0.0.1:11434.
```json
{
    "name": "rag_pipecone",
    "actor": {
        "type": "document.store.pipecone.PipeconeVS",
        "kwargs": {
            "embedding": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model": "llama3",
                    "base_url": "http://127.0.0.1:11434"
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