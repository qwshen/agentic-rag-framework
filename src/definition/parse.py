from .index import IndexDef
from .service import ServiceDef
from .types import Definition, ContextStore

class Parser:
    _CONTEXT_STORE_SECTION: str = "context_stores"
    _INDEX_SECTION: str = "indexing_def"
    _SERVICE_SECTION: str = "service_def"

    def __init__(self, env_file: str = None):
        self._env_file = env_file

    def parse(self, def_file: str) -> tuple[IndexDef, ServiceDef]:
        def_json = Definition.from_file(def_file, self._env_file)
        if not isinstance(def_json, dict):
            raise RuntimeError("Definition JSON must be in valid format")

        context_stores = []
        if Parser._CONTEXT_STORE_SECTION in def_json:
            if not isinstance(def_json[Parser._CONTEXT_STORE_SECTION], list):
                raise RuntimeError(f"The {Parser._CONTEXT_STORE_SECTION} section must be a list, but got {type(def_json[Parser._CONTEXT_STORE_SECTION])}")
        context_stores = [ContextStore.from_dict(store) for store in def_json.get(Parser._CONTEXT_STORE_SECTION, [])]
        if len(context_stores) == 0:
            raise RuntimeError("Context stores section cannot be empty")

        index_def: IndexDef = None
        if Parser._INDEX_SECTION in def_json:
            if not isinstance(def_json[Parser._INDEX_SECTION], list):
                raise RuntimeError(f"The {Parser._INDEX_SECTION} section must be a list, but got {type(def_json[Parser._INDEX_SECTION])}")
            index_def = IndexDef.from_dict(def_json[Parser._INDEX_SECTION], context_stores=context_stores)
        service_def: ServiceDef = None
        if self._SERVICE_SECTION in def_json:
            service_def = ServiceDef.from_dict(def_json[self._SERVICE_SECTION], context_stores=context_stores)
        return index_def, service_def

