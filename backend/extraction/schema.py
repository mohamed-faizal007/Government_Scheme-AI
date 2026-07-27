from typing import List
from pydantic import BaseModel, Field


class Metadata(BaseModel):
    scheme_name: str = ""
    scheme_type: str = ""
    state: str = ""
    implementing_department: str = ""
    category: str = ""


class Overview(BaseModel):
    description: str = ""
    objectives: List[str] = Field(default_factory=list)
    beneficiaries: List[str] = Field(default_factory=list)


class Benefits(BaseModel):
    financial_assistance: str = ""
    other_benefits: List[str] = Field(default_factory=list)


class Eligibility(BaseModel):
    conditions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)


class Application(BaseModel):
    mode: str = ""
    documents: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)


class Support(BaseModel):
    official_website: str = ""
    helpline: str = ""
    important_dates: List[str] = Field(default_factory=list)
    source_links: List[str] = Field(default_factory=list)


class FAQ(BaseModel):
    question: str = ""
    answer: str = ""


class SearchMetadata(BaseModel):
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class Scheme(BaseModel):
    metadata: Metadata = Metadata()
    overview: Overview = Overview()
    benefits: Benefits = Benefits()
    eligibility: Eligibility = Eligibility()
    application: Application = Application()
    support: Support = Support()
    faq: List[FAQ] = Field(default_factory=list)
    search_metadata: SearchMetadata = SearchMetadata()
    notes: str = ""