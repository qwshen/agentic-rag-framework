- To load a prompt from local, please use the following definition:
```json
{
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
    ]
}
```

- To load a prompt from a Hugging Face repository:
```json
    "prompts": [
        {
            "name": "chat_prompt",
            "actor": {
                "type": "huggingface_hub.hf_hub_download",
                "kwargs": {
                    "repo_id": "username/my-prompts",
                    "filename": "my-prompt.txt"
                }
            }                
        }
    ]
```