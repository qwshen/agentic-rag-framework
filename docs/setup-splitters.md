The following lists how to set up all supported document splitters.

#### 1. Text Splitters
```json
{
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
        ]
    }
}
```
Note: if the size of a chunk is less than **chunk_size_threshold**, the strategy given by **chunk_size_strategy** is applied.

#### 2. Semantic Chunkers
```json
{
    "splitting": {
        "actors": [
            {
                "type": "qwshen.document.splitting.semantic.SemanticSplitter",
                "kwargs": {
                    "worker": {
                        "type": "langchain_experimental.text_splitter.SemanticChunker",
                        "kwargs": {
                            "embeddings": {
                                "type": "langchain.embeddings.init_embeddings",
                                "kwargs": {
                                    "model":"${LLM_SPLITTING_MODEL}",
                                    "num_ctx": 640,
                                    "provider": "ollama",
                                    "base_url": "${LLM_SPLITTING_INFERENCE}"
                                }
                            },
                            "breakpoint_threshold_type": "standard_deviation",
                            "breakpoint_threshold_amount": 0.95
                        }
                    },
                    "chunk_size_threshold": 1024,
                    "chunk_size_strategy": "append"
                }
            }
        ]
    }
}
```

#### 3. Multiple Splitters
When multiple splitters are defined, the document is processed sequentially. The output from the first splitter is passed as input to the next splitter, and this process continues until all splitters have been applied.
```json
{
    "splitting": {
        "actors": [
            {
                "type": "qwshen.document.splitting.text.TextSplitter",
                "kwargs": {
                    "worker": {
                        "type": "langchain_text_splitters.character.RecursiveCharacterTextSplitter",
                        "kwargs": { 
                            "chunk_size": 2000,
                            "chunk_overlap": 0
                        }
                    }
                }
            },
            {
                "type": "qwshen.document.splitting.semantic.SemanticSplitter",
                "kwargs": {
                    "worker": {
                        "type": "langchain_experimental.text_splitter.SemanticChunker",
                        "kwargs": {
                            "embeddings": {
                                "type": "langchain.embeddings.init_embeddings",
                                "kwargs": {
                                    "model":"${LLM_SPLITTING_MODEL}",
                                    "num_ctx": 640,
                                    "provider": "ollama",
                                    "base_url": "${LLM_SPLITTING_INFERENCE}"
                                }
                            },
                            "breakpoint_threshold_type": "standard_deviation",
                            "breakpoint_threshold_amount": 0.95
                        }
                    },
                    "chunk_size_threshold": 1024,
                    "chunk_size_strategy": "append"
                }
            }
        ],
        "chunk_size_threshold": 1600,
        "chunk_size_strategy": "append"
    }
}
```

Note: **chunk_size_threshold** and **chunk_size_strategy** can be set up at splitter level and splitting level for all splitters. Please check [here](https://docs.langchain.com/oss/javascript/integrations/splitters) for details of all langchain text-splitters.