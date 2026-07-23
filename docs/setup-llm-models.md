The model section defines the LLM models to be used and specifies where inference is performed, either locally or remotely.

- Using OpenAI
```json
{
    "chat_models": [
        {
            "name": "it_learning_chat_model",
            "actor": {
                "type": "langchain_openai.ChatOpenAI",
                "kwargs": {
                    "base_url": "${LLM_CHAT_INFERENCE}/v1",
                    "model": "${LLM_CHAT_MODEL}",
                    "api_key": "it_learning",
                    "temperature": 0.35
                }
            }
        }
    ]
}
```

- Using ChatOllama
```json
{
    "chat_models": [
        {
            "name": "portfolio_tool_agent",
            "actor": {
                "type": "langchain_ollama.ChatOllama",
                "kwargs": {
                    "base_url": "${LLM_AGENT_INFERENCE}",
                    "model": "${LLM_AGENT_MODEL}"
                }
            }
        }
    ]
}
```