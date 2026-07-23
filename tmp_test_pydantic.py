from pydantic import BaseModel, ConfigDict, Field


class M(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    app_name: str = Field(default="A", alias="APP_NAME")


c = M(app_name="T")
print("init by field name:", c.app_name)
c2 = M(APP_NAME="T2")
print("init by alias:", c2.app_name)
print("dump:", c2.model_dump())
