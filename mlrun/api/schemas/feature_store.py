from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class Feature(BaseModel):
    name: str
    value_type: str

    class Config:
        orm_mode = True


class FeatureSetMetadata(BaseModel):
    name: str
    tag: Optional[str]
    labels: Optional[dict]
    updated: Optional[datetime]
    uid: Optional[str]


class FeatureSetSpec(BaseModel):
    entities: List[Feature]
    features: List[Feature]


class FeatureSet(BaseModel):
    metadata: FeatureSetMetadata
    spec: FeatureSetSpec
    status: Optional[dict]


class FeatureSetUpdate(BaseModel):
    features: Optional[List[Feature]]
    entities: Optional[List[Feature]]
    status: Optional[dict]
    labels: Optional[dict]


class FeatureSetRecord(BaseModel):
    id: int
    name: str
    project: str
    uid: str
    updated: Optional[datetime] = None
    entities: List[Feature]
    features: List[Feature]
    # state is extracted from the full status dict to enable queries
    state: Optional[str] = None
    status: Optional[dict] = None

    class Config:
        orm_mode = True


class FeatureSetsOutput(BaseModel):
    feature_sets: List[FeatureSet]