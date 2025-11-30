from dataclasses import dataclass, field
from typing import Dict

from .types import *


@dataclass(frozen=True)
class ServiceDef:
    context_stores: list[ContextStore] = field(default_factory=list)
    prompts: list[Prompt] = field(default_factory=list)
    chat_models: list[ChatModel] = field(default_factory=list)

    retrievals: list[Retrieval] = field(default_factory=list)

    searches: list[Search] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict, context_stores: list[ContextStore]) -> 'ServiceDef':
        return ServiceDef(
            context_stores=context_stores,
            prompts=[Prompt.from_dict(prompt) for prompt in data.get('prompts')],
            chat_models=[ChatModel.from_dict(model) for model in data.get('chat_models')],
            retrievals=[Retrieval.from_dict(retrieval) for retrieval in data.get('retrievals')],
            searches=[Search.from_dict(search) for search in data.get('searches', [])],
            services=[Service.from_dict(service) for service in data.get('services', [])]
        )