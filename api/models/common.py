from typing import Annotated

from bson import ObjectId
from pydantic import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(ObjectId(v)))]
