import os

from pydantic import BaseModel, HttpUrl, EmailStr, computed_field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class LinkBase(BaseModel):
    original_url: HttpUrl

    class Config:
        json_encoders = {
            HttpUrl: lambda v: str(v)
        }

class LinkCreate(LinkBase):
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        if isinstance(data['original_url'], HttpUrl):
            data['original_url'] = str(data['original_url'])
        return data


class LinkOut(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    user_id: Optional[int] = None

    @computed_field
    @property
    def short_url(self) -> str:
        base_url = os.getenv('BASE_URL')
        return f"{base_url}/{self.short_code}"

    class Config:
        from_attributes = True


class LinkStatsOut(BaseModel):
    original_url: HttpUrl
    created_at: datetime
    clicks: int
    last_clicked_at: Optional[datetime]

    class Config:
        orm_mode = True