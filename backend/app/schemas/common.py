from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case attrs <-> camelCase JSON/Firestore field names (doc §5)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
