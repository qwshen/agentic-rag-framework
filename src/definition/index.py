from dataclasses import dataclass, field

from .types import ContextStore, IndexActor

@dataclass(frozen=True)
class IndexDef:
    context_stores: list[ContextStore] = field(default_factory=list)
    actors: list[IndexActor] = field(default_factory=list)

    @staticmethod
    def from_dict(actors_def: list[dict], context_stores: list[ContextStore]) -> 'IndexDef':
        return IndexDef(
            context_stores=context_stores,
            actors=[IndexActor.from_dict(actor_def) for actor_def in actors_def])
