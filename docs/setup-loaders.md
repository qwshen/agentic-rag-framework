The following lists how to set up all supported document loaders.

#### 1. File Loader

##### 1.1 To load PDF files
```json
{
    "loading": {
        "actors": [
            {
                "actor": {
                    "type": "qwshen.document.loading.file.FileLoader",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/pdf",
                        "file_extensions": ".pdf",
                        "worker": {
                            "type": "langchain_community.document_loaders.pdf.PyPDFLoader",
                            "kwargs": {
                                "extract_images": false
                            }
                        }
                    }
                }
            },
            { ... }
        ]
    }
}    
``` 

##### 1.2 To load text files
```json
{
    "loading": {
        "actors": [
            {
                "actor": {
                    "type": "qwshen.document.loading.file.FileLoader",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/txt",
                        "file_extensions": ".txt",
                        "worker": {
                            "type": "langchain_community.document_loaders.text.TextLoader",
                            "kwargs": {
                                "encoding": "cp1252"
                            }
                        }
                    }
                }
            },
            { ... }
        ]
    }
}
```

##### 1.3 To load Word-documents
```json
{
    "loading": {
        "actors": [
            {
                "actor": {
                    "type": "qwshen.document.loading.file.FileLoader",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/doc",
                        "recursive": true,
                        "file_extensions": ".docx;.doc", 
                        "worker": {
                            "type": "langchain_community.document_loaders.word_document.UnstructuredWordDocumentLoader",
                            "kwargs": {
                                "mode": "single"
                            }
                        }
                    }
                }
            },
            { ... }
        ]
    }
}    
```

For details of various langchain document loaders, please check [here](https://docs.langchain.com/oss/javascript/integrations/providers/all_providers#document-loaders).

#### 2. Database Loader
```json
{
    "loading": {
        "actors": [
            {
                "actor": {
                    "type": "qwshen.document.loading.db.DbLoader",
                    "kwargs":{
                        "connection": "postgresql+psycopg://${DB_USER}:${DB_PWD}@${DB_HOST}:${DB_PORT}/${DB_NAME}",
                        "table_name": "news",
                        "columns": { 
                            "content": ["title", "content", "summary"],
                            "metadata": ["news_id", "published_date", "provider"]
                        },
                        "filter": {
                            "ts_column": "created_at",
                            "start_ts": "2025-01-01 00:00:00",
                            "end_ts": "20260-7-20 23:59:59"
                        }
                    }
                }
            }
            { ... }
        ]
    }
}    
```

- The selected content columns are concatenated into the document content using the format: "column1_name: column1_content; column2_name: column2_content; ...".
- The selected metadata columns are stored as metadata for each document corresponding to a row.
- The filter is optional.

#### 2. Setup schedules for Loaders
Schedules can be set up at loader level or loading level for all loaders. There are two types of schedulers:
- By file arrival event
- By cron-expression-based time event

```json
{
    "loading": {
        "actors": [
            {
                "actor": {
                    "type": "qwshen.document.loading.db.DbLoader",
                    "kwargs":{
                        "connection": "postgresql+psycopg://${DB_USER}:${DB_PWD}@${DB_HOST}:${DB_PORT}/${DB_NAME}",
                        "table_name": "news",
                        "columns": { 
                            "content": ["title", "content", "summary"],
                            "metadata": ["news_id", "published_date", "provider"]
                        },
                        "filter": {
                            "ts_column": "created_at"
                        }
                    }
                }
            },
            {
                "actor": {
                    "type": "qwshen.document.loading.file.FileLoader",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/txt",
                        "recursive": false,
                        "file_extensions": ".txt", 
                        "worker": {
                            "type": "langchain_community.document_loaders.text.TextLoader",
                            "kwargs": {
                                "autodetect_encoding": true
                            }
                        }
                    }
                },
                "scheduler": {
                    "type": "qwshen.common.scheduling.FileArrivalScheduler",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/txt",
                        "recursive": true
                    }        
                }
            },
            {
                "actor": {
                    "type": "qwshen.document.loading.file.FileLoader",
                    "kwargs": {
                        "directory": "${DOCUMENTS_DIRECTORY}/pdf",
                        "file_extensions": ".pdf",
                        "worker": {
                            "type": "langchain_community.document_loaders.pdf.PyPDFLoader",
                            "kwargs": {
                                "extract_images": false
                            }
                        }
                    }
                }
            }
        ],
        "scheduler": {
            "type": "qwshen.common.scheduling.CronScheduler",
            "kwargs": {
                "crons": ["15 11 * * *"]
            }
        }
    }
}    
```

- The File Arrival Scheduler is specifically for the text file loader. Whenever a new file arrives in the source directory, the file loader is automatically triggered.
- The daily scheduler, which runs at 11:15 AM every day, is used for all other loaders (excluding the text file loader). Any PDF files added for the PDF loader, as well as rows inserted or updated for the DbLoader between the previous day's 11:15 AM run and the current day's 11:15 AM run, will be loaded for indexing. Note: The created_at column is used as the timestamp reference for time-based filtering in the DbLoader.