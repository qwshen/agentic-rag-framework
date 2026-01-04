To run through all unit tests, please follow the following steps:

#### 1. Set up Ollama inference server locally
##### 1.1 Download and install Ollama
- Linux
  ```shell
  curl -sSL https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.gz -o ollama.tar.gz
  tar -xf ollama.tar.gz
  sudo mv ollama /usr/local/bin
  ```

- macOS
  ```shell
  brew install ollama
  ```

- Windows
  ```shell
  wsl --install
  curl -sSL https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.gz -o ollama.tar.gz
  tar -xf ollama.tar.gz
  sudo mv ollama /usr/local/bin
  ```  

- Docker
  ```shell
  docker pull ollama/ollama
  docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
  ```  

##### 1.2. Pull models
  ```shell
  ollama pull qwen3:8b
  ollama pull nomic-embed-text:v1.5
  ollama pull gpt-oss:20b
  ollama pull deepseek-r1:1.5b
  ```

  With docker
  ```shell
  docker exec -it ollama ollama pull qwen3:8b
  docker exec -it ollama ollama pull nomic-embed-text:v1.5
  docker exec -it ollama ollama pull gpt-oss:20b
  docker exec -it ollama ollama pull deepseek-r1:1.5b
  ```

##### 1.3. List models
  ```shell  
  ollama list  
  ```
 
  With docker
  ```shell  
  docker exec -it ollama ollama list  
  ```

#### 2. Prepare input documents
##### 2.1 create the following folders:
  ```shell
  mkdir -p /opt/agentic-rag-1.0.0
  chmod 777 -R /opt/agentic-rag-1.0.0

  mkdir -p /opt/agentic-rag-1.0.0/documents/pdf
  mkdir -p /opt/agentic-rag-1.0.0/documents/txt
  mkdir -p /opt/agentic-rag-1.0.0/documents/docx

  mkdir -p /opt/agentic-rag-1.0.0/db/faiss
  mkdir -p /opt/agentic-rag-1.0.0/db/chroma
  mkdir -p /opt/agentic-rag-1.0.0/db/qdrant
  mkdir -p /opt/agentic-rag-1.0.0/db/weaviate
  mkdir -p /opt/agentic-rag-1.0.0/db/milvus
  ```

##### 2.2 Copy documents
- please copy a few pdf files into /opt/agentic-rag-1.0.0/documents/pdf
- please copy a few txt files into /opt/agentic-rag-1.0.0/documents/txt
- please copy a few word-docx into /opt/agentic-rag-1.0.0/documents/docx

#### 3. Other setups
Each unit test may include setup instructions at the top of the file—please follow them to configure the required environment.