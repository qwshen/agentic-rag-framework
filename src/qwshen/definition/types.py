from dataclasses import dataclass, field
from typing import Any, Dict, List
import re
import os
import json
import hashlib

from qwshen.common import environment
from qwshen.common.logging import RagLogger

@dataclass(frozen=True)
class Actor:
    type: str
    kwargs: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Actor':
        return cls(type=data['type'], kwargs=data.get('kwargs', {}))

@dataclass(frozen=True)
class NamedActor:
    name: str
    actor: Actor = field(default_factory=Actor)

    @classmethod
    def from_dict(cls,data: Dict) -> 'NamedActor':
        return cls(name=data['name'], actor=Actor.from_dict(data.get('actor', {})))

@dataclass(frozen=True)
class ContextStore(NamedActor):
    pass

@dataclass(frozen=True)
class Scheduler(Actor):
    def id(self) -> str:
        return hashlib.sha256(json.dumps(self.__dict__).encode()).hexdigest()

@dataclass(frozen=True)
class LoadActor:
    actor: Actor
    scheduler: Scheduler = None

    @staticmethod
    def from_dict(data: Dict, default_scheduler: Scheduler) -> 'LoadActor':
        scheduler = Scheduler.from_dict(data.get('scheduler')) if data.get('scheduler') else default_scheduler
        return LoadActor(actor=Actor.from_dict(data['actor']), scheduler=scheduler)

@dataclass(frozen=True)
class Concurrency:
    workers: int = 3

    @staticmethod
    def from_dict(data: Dict) -> 'Concurrency':
        return Concurrency(workers=data.get('workers', 1))

@dataclass(frozen=True)
class ConcurrentActor:
    actor: Actor
    concurrency: Concurrency = field(default_factory=Concurrency)

    @staticmethod
    def from_dict(data: Dict) -> 'ConcurrentActor':
        return ConcurrentActor(actor=Actor.from_dict(data['actor']), concurrency=Concurrency.from_dict(data.get('concurrency', {})))

@dataclass(frozen=True)
class SplitActor(ConcurrentActor):
    pass

@dataclass(frozen=True)
class StoreActor:
    document_store: str = field(default='default_store')
    concurrency: Concurrency = field(default_factory=Concurrency)

    @staticmethod
    def from_dict(data: Dict) -> 'StoreActor':
        return StoreActor(document_store=data.get('document_store', 'default_store'), concurrency=Concurrency.from_dict(data.get('concurrency', {})))

@dataclass(frozen=True)
class IndexActor:
    name: str
    loaders: list[LoadActor]
    splitter: SplitActor
    indexer: StoreActor
    
    @staticmethod
    def from_dict(data: dict) -> 'IndexActor':
        load_def = data.get("loading", {})
        default_scheduler = Scheduler.from_dict(load_def.get('scheduler', {})) if 'scheduler' in load_def else None
        return IndexActor(
            name=data['name'],
            loaders=[LoadActor.from_dict(actor_def, default_scheduler) for actor_def in load_def.get('actors', [])],
            splitter=SplitActor.from_dict(data.get('splitting', {})),
            indexer=StoreActor.from_dict(data.get('indexing', {}))  
        )

@dataclass(frozen=True)
class Prompt(NamedActor):
    pass

@dataclass(frozen=True)
class ModelActor(Actor):
    pass

@dataclass(frozen=True)
class ChatModel:
    name: str
    actor: ModelActor=field(default_factory=ModelActor)

    @staticmethod
    def from_dict(data: Dict) -> 'ChatModel':
        return ChatModel(name=data['name'], actor=ModelActor.from_dict(data.get('actor', {})))


@dataclass(frozen=True)
class RetrievalActor(Actor):
    target_store: str = field(default='default_store')

    @staticmethod
    def from_dict(data: Dict) -> 'RetrievalActor':
        return RetrievalActor(type=data['type'], target_store=data.get('document_store'), kwargs=data.get('kwargs', {}))

@dataclass(frozen=True)
class Retrieval:
    name: str
    description: str
    search: RetrievalActor = field(default_factory=RetrievalActor)

    @staticmethod
    def from_dict(data: Dict) -> 'Retrieval':
        return Retrieval(name=data['name'], description=data['description'], search=RetrievalActor.from_dict(data.get('search')))

@dataclass(frozen=True)
class SearchActor:
    retrieval: str

    @staticmethod
    def from_dict(data: Dict) -> 'SearchActor':
        return SearchActor(retrieval=data['retrieval'])

@dataclass(frozen=True)
class Search:
    name: str
    definition: SearchActor
    access_roles: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict) -> 'Search':
        return Search(name=data['name'], definition=SearchActor.from_dict(data.get('definition', {})), access_roles=data.get('access_roles', []))    

@dataclass(frozen=True)
class ServicePromptWithHistory:
    enabled: bool = False
    use_summary:  bool = False
    window_k: int = -1

    @staticmethod
    def from_dict(data: Dict) -> 'ServicePromptWithHistory':
        window_k = data.get('window_k', -1)
        use_summary = data.get('use_summary', False)
        return ServicePromptWithHistory(enabled=(window_k > 0), use_summary=use_summary, window_k=window_k)

@dataclass(frozen=True)
class ServicePrompt:
    ref_prompt: str
    with_history: ServicePromptWithHistory = field(default_factory=ServicePromptWithHistory)

    @staticmethod
    def from_dict(data: Dict) -> 'ServicePrompt':
        return ServicePrompt(ref_prompt=data['ref'], with_history=ServicePromptWithHistory.from_dict(data.get('with_history', {})))

@dataclass(frozen=True)
class ServiceContextAgent:
    ref_model: str

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceContextAgent':
        return ServiceContextAgent(ref_model=data.get('ref_model', None))

@dataclass(frozen=True)
class ServiceContext:
    ref_retrievals: list[str]
    agent: ServiceContextAgent = field(default_factory=ServiceContextAgent)

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceContext':
        return ServiceContext(ref_retrievals=data['ref_retrievals'], agent=ServiceContextAgent.from_dict(data.get("agent", {})))

@dataclass(frozen=True)
class ServiceGenerationAgent:
    ref_prompt: str
    ref_model: str

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceGenerationAgent':
        return ServiceGenerationAgent(ref_prompt=data.get('ref_prompt', ''), ref_model=data.get('ref_model', ''))

@dataclass(frozen=True)
class ServiceGenerationAnswerRewriting(ServiceGenerationAgent):
    pass

@dataclass(frozen=True)
class ServiceGeneration:
    ref_model: str
    answer_rewriting: ServiceGenerationAnswerRewriting = field(default_factory=ServiceGenerationAnswerRewriting)

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceGeneration':
        return ServiceGeneration(ref_model=data['ref_model'], answer_rewriting=ServiceGenerationAnswerRewriting.from_dict(data.get('answer_rewriting', {})))

@dataclass(frozen=True)
class ServiceAgentivityQueryRefining(ServiceGenerationAgent):
    pass

@dataclass(frozen=True)
class ServiceAgentivityDocumentGrading(ServiceGenerationAgent):
    accept_gradedness_answers: list[str]
    reject_gradedness_answers: list[str]
    min_threshold_score: float
    max_iterations: int

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceAgentivityDocumentGrading':
        return ServiceAgentivityDocumentGrading(
            ref_prompt=data.get('ref_prompt', ''), ref_model=data.get('ref_model', ''),
            accept_gradedness_answers=data.get('accept_gradedness_answers', ['relevant']), 
            reject_gradedness_answers=data.get('reject_gradedness_answers', ['irrelevant']), 
            min_threshold_score=data.get('min_threshold_score', 0.5), 
            max_iterations=data.get('max_iterations', 2)
        )

@dataclass(frozen=True)
class ServiceAgentivityAnswerGrounding(ServiceGenerationAgent):
    accept_groundedness_answers: list[str]
    reject_groundedness_answers: list[str]
    max_iterations: int

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceAgentivityAnswerGrounding':
        return ServiceAgentivityAnswerGrounding(
            ref_prompt=data.get('ref_prompt', ''), ref_model=data.get('ref_model', ''),
            accept_groundedness_answers=data.get('accept_groundedness_answers', ['yes']), 
            reject_groundedness_answers=data.get('reject_groundedness_answers', ['no']), 
            max_iterations=data.get('max_iterations', 3)
        )

@dataclass(frozen=True)
class ServiceAgentivity:
    query_refining: ServiceAgentivityQueryRefining = field(default_factory=ServiceAgentivityQueryRefining)
    document_grading: ServiceAgentivityDocumentGrading = field(default_factory=ServiceAgentivityDocumentGrading)
    answer_grounding: ServiceAgentivityAnswerGrounding = field(default_factory=ServiceAgentivityAnswerGrounding)

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceAgentivity':
        return ServiceAgentivity(
            query_refining = ServiceAgentivityQueryRefining.from_dict(data.get('query_refining', {})),
            document_grading = ServiceAgentivityDocumentGrading.from_dict(data.get('document_grading', {})),
            answer_grounding = ServiceAgentivityAnswerGrounding.from_dict(data.get('answer_grounding', {}))
        )

@dataclass(frozen=True)
class ServiceActor:
    prompt: ServicePrompt = field(default_factory=ServicePrompt)
    context: ServiceContext = field(default_factory=ServiceContext)
    generation: ServiceGeneration = field(default_factory=ServiceGeneration)
    agentivity: ServiceAgentivity = field(default_factory=ServiceAgentivity)

    @staticmethod
    def from_dict(data: Dict) -> 'ServiceActor':
        return ServiceActor(
            prompt=ServicePrompt.from_dict(data['prompt']), 
            context=ServiceContext.from_dict(data['context']), 
            generation=ServiceGeneration.from_dict(data['generation']), 
            agentivity=ServiceAgentivity.from_dict(data.get('agentivity', {}))
        )

@dataclass(frozen=True)
class Service:
    name: str
    definition: ServiceActor
    access_roles: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict) -> 'Service':
        return Service(name=data['name'], definition=ServiceActor.from_dict(data['definition']), access_roles=data.get('access_roles', []))


@dataclass(frozen=True)
class Definition:
    @staticmethod
    def resolve(v):
        if isinstance(v, str):
            vars = re.findall("\\$\\{([^\\$|\\{|\\}]*)\\}", v)
            if vars and len(vars) > 0:
                for var in vars:
                    if var not in os.environ:
                        raise RuntimeError(f"Environment variable {var} is not defined.")
                    v = v.replace("${" + var + "}", Definition.resolve(os.environ[var]))
        return v

    @staticmethod    
    def resolve_list(l: list):
        return [Definition.resolve_dict(e) if isinstance(e, dict) else (Definition.resolve_list(e) if isinstance(e, list) else Definition.resolve(e)) for e in l]
    
    @staticmethod
    def resolve_dict(kv: dict):
        for k, v in kv.items():
            if isinstance(v, dict):
                kv[k] = Definition.resolve_dict(v)
            elif isinstance(v, list):
                kv[k] = Definition.resolve_list(v)
            else:
                kv[k] = Definition.resolve(v)
        return kv

    @staticmethod
    def from_file(def_file: str, env_file: str) -> str:
        os.environ["APPLICATION_DIR"] = os.getcwd()

        if not os.path.isfile(def_file) or (env_file is not None and not os.path.isfile(env_file)):
            raise RuntimeError(f"Either the definition file [{def_file}] or the environment file [{env_file}] doesn't exist")

        def_json = None
        with open(def_file, "r") as json_file:
            def_json = json.load(json_file)
        if def_json is None:
            raise RuntimeError("definition is not provided or not in valid json format.")

        if env_file is not None:
            environment.setup(env_file)
        def_json = Definition.resolve_dict(def_json) if isinstance(def_json, dict) else (Definition.resolve_list(def_json) if isinstance(def_json, list) else def_json)

        RagLogger.setup(def_json.get("logging", None))
        return def_json

