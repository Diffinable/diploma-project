from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base, str_256, datetime_now


class Clients(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str_256]
    email: Mapped[str_256]
    phone: Mapped[str_256 | None]
    created_at: Mapped[datetime_now]
    
    user = relationship("Users", back_populates="client")
    premises: Mapped[list["Premises"]] = relationship(back_populates="client")
    estimates: Mapped[list["Estimates"]] = relationship(back_populates="client")

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str_256] = mapped_column(unique=True)
    hashed_password: Mapped[str_256]
    created_at: Mapped[datetime_now]

    client = relationship("Clients", uselist=False, back_populates="user")



class Premises(Base):
    __tablename__ = "premises"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    area: Mapped[float]
    height: Mapped[float]
    created_at: Mapped[datetime_now]

    client: Mapped["Clients"] = relationship(back_populates="premises")
    estimates: Mapped[list["Estimates"]] = relationship(back_populates="premise")





class WorkTypes(Base):
    __tablename__ = "work_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str_256]
    category: Mapped[str_256]
    unit: Mapped[str_256]
    material_consumption: Mapped[float]
    labor_cost_per_unit: Mapped[float]
    complexity_factor: Mapped[float] = mapped_column(default=1.0)
    material_profile_id: Mapped[int | None] = mapped_column(ForeignKey("material_profiles.id"), nullable=True)


    material_profile: Mapped["MaterialProfiles"] = relationship("MaterialProfiles", back_populates="work_types")
    estimates: Mapped[list["Estimates"]] = relationship(
        back_populates="work_types",
        secondary="estimate_work_types",
    )




estimate_work_types = Table(
    "estimate_work_types",
    Base.metadata,
    Column("volume", Float, nullable=False),
    Column("estimate_id", Integer, ForeignKey("estimates.id"), primary_key=True),
    Column("work_type_id", Integer, ForeignKey("work_types.id"), primary_key=True),
)


class Brigades(Base):
    __tablename__ = "brigades"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str_256]



class MaterialProfiles(Base):
    __tablename__ = "material_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str_256]
    cost_per_unit: Mapped[float]
    category: Mapped[str_256 | None]
    
    work_types: Mapped[list["WorkTypes"]] = relationship("WorkTypes", back_populates="material_profile")

class Estimates(Base):
    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    premise_id: Mapped[int] = mapped_column(ForeignKey("premises.id"))
    total_cost: Mapped[float]
    total_material_cost: Mapped[float] = mapped_column(default=0.0)  # Добавлено
    total_labor_cost: Mapped[float] = mapped_column(default=0.0)  # Добавлено
    created_at: Mapped[datetime_now]

    client: Mapped["Clients"] = relationship(back_populates="estimates")
    premise: Mapped["Premises"] = relationship(back_populates="estimates")

    work_types: Mapped[list["WorkTypes"]] = relationship(
        secondary=estimate_work_types,
        back_populates="estimates"
    )




