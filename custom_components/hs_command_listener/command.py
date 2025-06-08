import json
from dataclasses import dataclass, fields, is_dataclass
from typing import Type, TypeVar, Any, Dict, Optional

T = TypeVar('T', bound='JsonDataclass')

class JsonDataclass:
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass to use JsonDataclass")
        
        # Extract only matching fields to avoid extra junk in the input
        field_names = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        obj = cls(**filtered_data)
        if hasattr(obj, 'post_init'):
            obj.post_init()
        return obj


@dataclass
class Command(JsonDataclass):
    command: str
    type: str
    entityID: str
    name: Optional[str] = None  
    force: bool = True
    min: float = None
    max: float = None

    def post_init(self):
        self.name = self.name.strip()
        self.entityID = self.entityID.strip().lower().replace(" ", "_")
        if not hasattr(self, "force") or self.force is None:
            self.force = True

    # called automatically after __init__
    def __post_init__(self) -> None:
        # If name is omitted or empty, use entityID
        if not self.name:
            self.name = self.entityID

    @classmethod
    def from_json(cls, json_str: str) -> "Command":
        # allow pretty-printed JSON
        clean = json_str.replace("\r", "").replace("\n", "")
        return cls(**json.loads(clean))
