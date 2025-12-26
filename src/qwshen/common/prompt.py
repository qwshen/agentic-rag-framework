from pathlib import Path
import json
import yaml

from langchain_core.prompts.loading import type_to_loader_dict
from langchain_core.prompts.base import BasePromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate

def _load_chat_prompt(config: dict) -> ChatPromptTemplate:
    input_variables = set(config.pop("input_variables"))
    messages = config.pop("messages")

    first_message = messages.pop(0)
    template = first_message["prompt"].pop("template") if first_message else None
    if not template:
        raise ValueError("Can't load chat prompt without template")
    chat_prompt = ChatPromptTemplate.from_template(template=template, **config)
    input_variables |= set(chat_prompt.input_variables)

    for message in messages:
        template = message["prompt"].pop("template") if message else None
        if template is not None:
            chat_prompt.messages.append(ChatPromptTemplate.from_template(template=template, **config))
            input_variables |= set(chat_prompt.input_variables)
    chat_prompt.input_variables = list(input_variables)
    return chat_prompt

def load_from_file(path: str, encoding: str | None = None) -> BasePromptTemplate:
    config: dict = {}
    file_path = Path(path)
    if file_path.suffix == ".json":
        with file_path.open(encoding=encoding) as f:
            config = json.load(f)
    elif file_path.suffix.endswith((".yaml", ".yml")):
        with file_path.open(encoding=encoding) as f:
            config = yaml.safe_load(f)
    else:
        raise ValueError("Invalid file format. Only json or yaml formats are supported.")
    
    config_type = config.pop("_type", "prompt")
    if config_type not in type_to_loader_dict:
        raise ValueError(f"Loading {config_type} prompt not supported")

    prompt_loader = _load_chat_prompt if config_type == "chat" else type_to_loader_dict[config_type]
    return prompt_loader(config)

