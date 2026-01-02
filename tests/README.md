#### 1. To run through all unit tests, please set up Ollama inference server locally as follows:
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

#### 2. Pull models
  ```shell
  ollama pull qwen3:8b
  ollama pull nomic-embed-text:v1.5
  ollama pull gpt-oss:20b
  ollama pull mistral:7b
  ollama pull llama3.2
  ollama pull deepseek-r1:1.5b
  ```

  With docker
  ```shell
  docker exec -it ollama ollama pull qwen3:8b
  docker exec -it ollama ollama pull nomic-embed-text:v1.5
  docker exec -it ollama ollama pull gpt-oss:20b
  docker exec -it ollama ollama pull mistral:7b
  docker exec -it ollama ollama pull llama3.2
  docker exec -it ollama ollama pull deepseek-r1:1.5b
  ```

#### 3. List models
  ```shell  
  ollama list  
  ```
 
  With docker
  ```shell  
  docker exec -it ollama ollama list  
  ```
