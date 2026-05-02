#### 1. Set up the runtime environment as follows:

    - Install Python 3.10+ and set up a virutla environment
      - Install required packages
      ```shell
        pip install -r ./requirements.txt
      ```
    - Set up the project
      ```shell
        pip install . -e
      ```

#### 2. Setup LLM models inference as follows locally:

    ```shell
    docker pull ollama/ollama
    docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
    ```  

Pull models

    ```shell
    docker exec -it ollama ollama pull llama3.2
    docker exec -it ollama ollama pull nomic-embed-text:v1.5
    ```

Update app.env as follows:

    ```
    LLM_SPLITTING_INFERENCE="http://127.0.0.1:11434"
    LLM_SPLITTING_MODEL="nomic-embed-text:v1.5"

    LLM_EMBEDDINGS_INFERENCE="http://127.0.0.1:11434"
    LLM_EMBEDDINGS_MODEL="nomic-embed-text:v1.5"

    LLM_CHAT_INFERENCE="http://127.0.0.1:11434"
    LLM_CHAT_MODEL="llama3.2"

    LLM_REASONING_INFERENCE="http://127.0.0.1:11434"
    LLM_REASONING_MODEL="llama3.2"

    LLM_AGENT_INFERENCE="http://127.0.0.1:11434"
    LLM_AGENT_MODEL="llama3.2"
    ```

#### 3. Create a document root folder, such as "/opt/agentic-rag-1.0.0/documents/it-learning", and create pdf, txt, and doc subfolders. Collect and place documents (pdf, docx, txt, etc.) into different subfolder accordingly:

    - Update *DOCUMENT_DIRECTORY* in app.env if it is different from */opt/agentic-rag-1.0.0/documents/it-learning*
      ```
      DOCUMENTS_DIRECTORY=/opt/agentic-rag-1.0.0/documents/it-learning
      ```

Note: for documents organized in differnt structure, please update index.json for document loaders.

#### 4. Set up a PostgreSQL instance with pgvector extension locally with the following commands:

    ```shell
    docker pull pgvector/pgvector:pg16
    docker run --name pgvector-container -e POSTGRES_USER=raguser -e POSTGRES_PASSWORD=ragpwd -e POSTGRES_DB=rag_pg -p 6024:5432 -d pgvector/pgvector:pg16
    ```

Once the PostgreSQL instance is up and running, update app.env as follows:
    ```
    POSTGRES_HOST="127.0.0.1"
    POSTGRES_PORT=6024
    POSTGRES_DB=rag_pg
    POSTGRES_USER=raguser
    POSTGRES_PASSWORD=ragpwd
    ```

#### 5. Start the indexing in tutorial folder with the following command:

    ```shell
    python ./index.py
    ```

Connect to the PostgreSQL instance, and check documents are indexed in rag_pg database. 

Please wait till all documents got indexed before moving to next step.


#### 6. Start chat
    ```shenn
    python chat.py
    ```