from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, EmailStr

class ClientCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str]

class Client(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str]
    created_at: datetime

class PremiseCreate(BaseModel):
    client_id: int
    area: float
    height: float

class Premise(BaseModel):
    id: int
    client_id: int
    area: float
    height: float
    created_at: datetime

class WorkTypeCreate(BaseModel):
    name: str
    unit: str
    material_consumption: float
    labor_cost_per_unit: float
    complexity_factor: float = 1.0
    material_profile_id: Optional[int] = None

class WorkType(BaseModel):
    id: int
    name: str
    unit: str
    material_consumption: float
    labor_cost_per_unit: float
    complexity_factor: float
    material_profile_id: Optional[int] = None


class WorkTypeVolume(BaseModel):
    id: int
    volume: float

class WorkTypeDetail(BaseModel):
    name: str
    units: float
    labor_cost: float
    material_cost: float = 0.0
    unit: str

class BrigadeCreate(BaseModel):
    name: str
    contact_phone: str
    contact_email: str

class Brigade(BaseModel):
    id: int
    name: str
    contact_phone: str
    contact_email: str

class BrigadeWorkRatesCreate(BaseModel):
    brigade_id: int
    work_type_id: int
    labor_cost_per_unit: float
    complexity_factor: float = 1.0

class BrigadeWorkRates(BaseModel):
    id: int
    brigade_id: int
    work_type_id: int
    labor_cost_per_unit: float
    complexity_factor: float

class MaterialCreate(BaseModel):
    name: str

class Material(BaseModel):
    id: int
    name: str

class MaterialProfileCreate(BaseModel):
    material_id: int
    name: str
    volume: float
    cost_per_unit: float

class MaterialProfile(BaseModel):
    id: int
    material_id: int
    name: str
    volume: float
    cost_per_unit: float

class MaterialPriceCategories(BaseModel):
    id: int
    material_id: int
    budget_price: float
    average_price: float
    high_quality_price: float

class EstimateCreate(BaseModel):
    client_id: int
    premise_id: int
    work_types: List[WorkTypeVolume]

class EstimateNoSave(BaseModel):
    area: Optional[float] = None
    height: Optional[float] = None
    work_types: List[WorkTypeVolume]

class Estimate(BaseModel):
    id: int
    total_cost: float
    total_labor_cost: float  # Добавлено
    total_material_cost: float = 0.0  # Добавлено
    work_types: List[WorkTypeDetail]
    created_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str