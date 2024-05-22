from pydantic import BaseModel, ConfigDict


class CustomAttribute(BaseModel):
    model_config = ConfigDict(from_attributes=True)
