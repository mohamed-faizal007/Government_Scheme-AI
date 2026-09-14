from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    income_annual: Optional[float] = None
    category: Optional[str] = None
    is_student: Optional[bool] = None
    is_employed: Optional[bool] = None
    occupation: Optional[str] = None
    disability: Optional[bool] = None
    is_ex_serviceman: Optional[bool] = None
