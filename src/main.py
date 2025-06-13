from datetime import datetime
from typing import Annotated
from sqlalchemy import create_engine, update
from src.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker
from sqlalchemy import String, text, insert

sync_engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
    echo=True,
)
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=True,
)

session_factory = sessionmaker(sync_engine)
async_session_factory = async_sessionmaker(async_engine)

str_256 = Annotated[str, 256]
float_nullable = Annotated[float, mapped_column(nullable=True)]
datetime_now = Annotated[datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]

class Base(DeclarativeBase):
    type_annotation_map = {
        str_256: String(256)
    }
    def __repr__(self):
        cols = [f"{col}={getattr(self, col)}" for col in self.__table__.columns.keys()[:3]]
        return f"<{self.__class__.__name__} {','.join(cols)}>"

import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.models.repairs import Clients, MaterialProfiles, WorkTypes
from src.database import sync_engine, Base, async_session_factory
from contextlib import asynccontextmanager
from src.api.repairs import router as repairs_router

@asynccontextmanager
async def lifespan(app: FastAPI):    
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    async with async_session_factory() as session: 
        await session.execute(insert(Clients), [
            {"name": "Гость", "email": "guest@example.com", "phone": None}
        ])   
        
        await session.execute(insert(WorkTypes), [
            # Existing work types with updated material_consumption and original units
            {
                "name": "Удаление старых обоев со стен",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 0.0,  # No material
                "labor_cost_per_unit": 38,
                "complexity_factor": 1.0
            },
            {
                "name": "Очистка стен от масляной краски",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 0.0,  # No material
                "labor_cost_per_unit": 145,
                "complexity_factor": 1.2
            },
            {
                "name": "Штукатурка стен по маякам до 30 мм",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 15.0,  # 15 kg/м²
                "labor_cost_per_unit": 360,
                "complexity_factor": 1.0
            },
            {
                "name": "Установка малярных уголков",
                "category": "стены",
                "unit": "м.п.",
                "material_consumption": 0.1,  # 0.1 kg/м.п.
                "labor_cost_per_unit": 20,
                "complexity_factor": 1.0
            },
            {
                "name": "Грунтование стен (1 слой)",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 0.2,  # 0.2 liters/м²
                "labor_cost_per_unit": 40,
                "complexity_factor": 1.0
            },
            {
                "name": "Окрашивание стен водоэмульсионной краской",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 0.3,  # 0.3 liters/м²
                "labor_cost_per_unit": 226,
                "complexity_factor": 1.0
            },
            {
                "name": "Облицовка стен плиткой",
                "category": "стены",
                "unit": "м²",
                "material_consumption": 2.0,  # 2 kg/м² (adhesive)
                "labor_cost_per_unit": 480,
                "complexity_factor": 1.0
            },
            {
                "name": "Установка багета",
                "category": "стены",
                "unit": "м.п.",
                "material_consumption": 0.2,  # 0.2 kg/м.п.
                "labor_cost_per_unit": 302,
                "complexity_factor": 1.0
            },
            {
                "name": "Устройство отверстия в плитке до 25 мм",
                "category": "стены",
                "unit": "шт.",
                "material_consumption": 0.0,  # No material
                "labor_cost_per_unit": 120,
                "complexity_factor": 1.0
            },
            # Work types for "полы" category
            {
                "name": "Обработка пола грунтовкой в 1 слой",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.2,  # 0.2 liters/м²
                "labor_cost_per_unit": 50,
                "complexity_factor": 1.0
            },
            {
                "name": "Обработка пола бетон-контактом",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.3,  # 0.3 liters/м²
                "labor_cost_per_unit": 150,
                "complexity_factor": 1.0
            },
            {
                "name": "Цементная стяжка пола (ЦПС) до 5см",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 15.0,  # 15 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.2
            },
            {
                "name": "Цементная стяжка пола (ЦПС) до 7см",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 18.0,  # 18 kg/м²
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.2
            },
            {
                "name": "Стяжка с керамзитом (ЦПС+керамзит) до 10см",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 20.0,  # 20 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.3
            },
            {
                "name": "Стяжка с керамзитом (ЦПС+керамзит) до 20см",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 25.0,  # 25 kg/м²
                "labor_cost_per_unit": 800,
                "complexity_factor": 1.3
            },
            {
                "name": "Наливные полы из самовыравнивающейся смеси",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 5.0,  # 5 liters/м²
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.1
            },
            {
                "name": "Наливные полы из самовыравнивающейся смеси объем до 10м²",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 7.0,  # 7 liters/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Армирование цементно-песчаной стяжки сеткой",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.5,  # 0.5 kg/м²
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка пароизоляции, пенофола",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.1,  # 0.1 kg/м²
                "labor_cost_per_unit": 100,
                "complexity_factor": 1.0
            },
            {
                "name": "Утепление пола (минвата, пенопласт)",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 3.0,  # 3 kg/м²
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.1
            },
            {
                "name": "Монтаж лаг для пола",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 1.0,  # 1 kg/м.п.
                "labor_cost_per_unit": 400,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка фанеры, ДСП по лагам",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.0,  # 2 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Шпатлевание фанеры, ДСП",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.5,  # 0.5 kg/м²
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка бытового линолеума, ковролина",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.0,  # 1 kg/м² (adhesive)
                "labor_cost_per_unit": 400,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка полукоммерческого линолеума",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.2,  # 1.2 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка коммерческого линолеума",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.5,  # 1.5 kg/м²
                "labor_cost_per_unit": 600,
                "complexity_factor": 1.0
            },
            {
                "name": "Проклеивание основания под линолеум",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.3,  # 0.3 kg/м²
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Холодная сварка швов линолеума",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.05,  # 0.05 kg/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка кварцвиниловой плитки на клею",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.0,  # 2 kg/м²
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка кварцвиниловой плитки с замком",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.5,  # 1.5 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Укладка кафельной плитки со одной из сторон менее 300 мм",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 3.0,  # 3 kg/м²
                "labor_cost_per_unit": 2200,
                "complexity_factor": 1.3
            },
            {
                "name": "Укладка плитки с одной из сторон менее 500 мм",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.5,  # 2.5 kg/м²
                "labor_cost_per_unit": 2000,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка керамогранита 600х600 мм",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.0,  # 2 kg/м²
                "labor_cost_per_unit": 1800,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка керамогранита 1200х600 мм",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.5,  # 2.5 kg/м²
                "labor_cost_per_unit": 2700,
                "complexity_factor": 1.3
            },
            {
                "name": "Укладка мозаики на пол (в картах)",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 3.0,  # 3 kg/м²
                "labor_cost_per_unit": 3000,
                "complexity_factor": 1.4
            },
            {
                "name": "Укладка шестигранной плитки - соты",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 3.0,  # 3 kg/м²
                "labor_cost_per_unit": 3200,
                "complexity_factor": 1.4
            },
            {
                "name": "Затирка швов до 600х600 мм цементной затиркой",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.5,  # 0.5 kg/м²
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Затирка швов мозаики и шестигранной цементной затиркой",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.7,  # 0.7 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Затирка швов полимерной затиркой",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 0.6,  # 0.6 kg/м²
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Укладка плитки со смещением",
                "category": "полы",
                "unit": "%",
                "material_consumption": 0.0,  # No additional material
                "labor_cost_per_unit": 20,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка плитки по диагонали",
                "category": "полы",
                "unit": "%",
                "material_consumption": 0.0,  # No additional material
                "labor_cost_per_unit": 20,
                "complexity_factor": 1.2
            },
            {
                "name": "Укладка плитки с декоративными вставками",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 2.5,  # 2.5 kg/м²
                "labor_cost_per_unit": 2500,
                "complexity_factor": 1.3
            },
            {
                "name": "Укладка ламината до 10 мм",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.0,  # 1 kg/м² (adhesive)
                "labor_cost_per_unit": 400,
                "complexity_factor": 1.0
            },
            {
                "name": "Укладка паркетной доски",
                "category": "полы",
                "unit": "м²",
                "material_consumption": 1.5,  # 1.5 kg/м²
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.1
            },
            {
                "name": "Обработка швов ламината, доски герметиком",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.1,  # 0.1 kg/м.п.
                "labor_cost_per_unit": 70,
                "complexity_factor": 1.0
            },
            {
                "name": "Переходной порожек металл",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.5,  # 0.5 kg/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Переходной порожек ПВХ",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.3,  # 0.3 kg/м.п.
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Монтаж ПВХ плинтуса",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.5,  # 0.5 kg/м.п.
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Монтаж плинтус МДФ, дюрополимер",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.7,  # 0.7 kg/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Торцевание плинтусов МДФ, дюрополимер",
                "category": "полы",
                "unit": "шт.",
                "material_consumption": 0.2,  # 0.2 kg/unit
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.1
            },
            {
                "name": "Покраска плинтуса в 1 слой",
                "category": "полы",
                "unit": "м.п.",
                "material_consumption": 0.1,  # 0.1 liters/м.п.
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            # Work types for "потолок" category
            {
                "name": "Нанесение грунтовки глубокого проникновения в 1 слой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.2,  # 0.2 liters/м²
                "labor_cost_per_unit": 80,
                "complexity_factor": 1.0
            },
            {
                "name": "Нанесение грунтовки бетон-контакт",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.3,  # 0.3 liters/м²
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Запенивание рустов с подрезкой",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 0.1,  # 0.1 kg/м.п.
                "labor_cost_per_unit": 150,
                "complexity_factor": 1.0
            },
            {
                "name": "Выравнивание потолка гипсовой штукатуркой по маякам",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 5.0,  # 5 kg/м²
                "labor_cost_per_unit": 2000,
                "complexity_factor": 1.3
            },
            {
                "name": "Шпатлевание потолка под обои/стеклохолст в 1 слой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.5,  # 0.5 kg/м²
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Оклейка потолка стеклохолстом, сеткой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.3,  # 0.3 kg/м²
                "labor_cost_per_unit": 400,
                "complexity_factor": 1.0
            },
            {
                "name": "Шпатлевание стеклохолста суперфинишем в 1 слой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.4,  # 0.4 kg/м²
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Шлифование потолка под покраску",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.0,  # No material
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Покраска потолка в 1 слой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.2,  # 0.2 liters/м²
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Потолок из гипсокартона одноуровневый в 1 слой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 2.0,  # 2 kg/м²
                "labor_cost_per_unit": 1500,
                "complexity_factor": 1.2
            },
            {
                "name": "Потолок из гипсокартона одноуровневый в 2 слоя",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 3.0,  # 3 kg/м²
                "labor_cost_per_unit": 2000,
                "complexity_factor": 1.3
            },
            {
                "name": "Потолок из гипсокартона двухуровневый простой",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 3.5,  # 3.5 kg/м²
                "labor_cost_per_unit": 2500,
                "complexity_factor": 1.4
            },
            {
                "name": "Потолок из гипсокартона двухуровневый сложный",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 4.0,  # 4 kg/м²
                "labor_cost_per_unit": 3000,
                "complexity_factor": 1.5
            },
            {
                "name": "Ниша в ГКЛ потолке",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 1.0,  # 1 kg/м.п.
                "labor_cost_per_unit": 1500,
                "complexity_factor": 1.3
            },
            {
                "name": "Покраска потолка из гипсокартона двухуровневого в 1 слой",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 0.2,  # 0.2 liters/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Багет потолочный пенопласт монтаж с покраской",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 0.5,  # 0.5 kg/м.п.
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.0
            },
            {
                "name": "Багет потолочный полиуретан монтаж с покраской",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 0.7,  # 0.7 kg/м.п.
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.0
            },
            {
                "name": "Багет потолочный запил углов",
                "category": "потолок",
                "unit": "шт.",
                "material_consumption": 0.1,  # 0.1 kg/unit
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Потолок из панелей ПВХ по каркасу",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 1.0,  # 1 kg/м²
                "labor_cost_per_unit": 800,
                "complexity_factor": 1.1
            },
            {
                "name": "Потолок реечный по каркасу",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 1.2,  # 1.2 kg/м²
                "labor_cost_per_unit": 1000,
                "complexity_factor": 1.2
            },
            {
                "name": "Потолок 'Армстронг' в помещении до 3 м",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 0.8,  # 0.8 kg/м²
                "labor_cost_per_unit": 600,
                "complexity_factor": 1.0
            },
            {
                "name": "Монтаж потолка 'Армстронг' в помещении от 3 м",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 1.0,  # 1 kg/м²
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.0
            },
            {
                "name": "Потолок 'Грильято' в помещении до 3 м",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 1.0,  # 1 kg/м²
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.1
            },
            {
                "name": "Монтаж потолка 'Грильято' в помещении от 3 м",
                "category": "потолок",
                "unit": "м²",
                "material_consumption": 1.2,  # 1.2 kg/м²
                "labor_cost_per_unit": 800,
                "complexity_factor": 1.1
            },
            {
                "name": "Установка гардины потолочной ПВХ",
                "category": "потолок",
                "unit": "м.п.",
                "material_consumption": 0.5,  # 0.5 kg/м.п.
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.0
            },
            {
                "name": "Установка точечного светильника в потолок",
                "category": "потолок",
                "unit": "шт.",
                "material_consumption": 0.2,  # 0.2 kg/unit
                "labor_cost_per_unit": 350,
                "complexity_factor": 1.0
            },
            # Work types for "двери-окна" category
            {
                "name": "Подгон дверных проемов под установочный размер гипс",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.5,  # 0.5 kg/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Подгон дверных проемов под установочный размер кирпич",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.7,  # 0.7 kg/м.п.
                "labor_cost_per_unit": 400,
                "complexity_factor": 1.1
            },
            {
                "name": "Подгон дверных проемов под установочный размер бетон (рез до 20 см)",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 1.0,  # 1 kg/м.п.
                "labor_cost_per_unit": 800,
                "complexity_factor": 1.2
            },
            {
                "name": "Откосы оконные установка примыкающего профиля",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.3,  # 0.3 kg/м.п.
                "labor_cost_per_unit": 200,
                "complexity_factor": 1.0
            },
            {
                "name": "Откосы оконные выравнивание под покраску",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 1.0,  # 1 kg/м.п.
                "labor_cost_per_unit": 1000,
                "complexity_factor": 1.2
            },
            {
                "name": "Откосы оконные оклейка стеклохолстом",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.2,  # 0.2 kg/м.п.
                "labor_cost_per_unit": 300,
                "complexity_factor": 1.0
            },
            {
                "name": "Откосы оконные шпатлевание по стеклохолсту",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.3,  # 0.3 kg/м.п.
                "labor_cost_per_unit": 250,
                "complexity_factor": 1.0
            },
            {
                "name": "Откосы оконные покраска в/э краской в 2 слоя",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.4,  # 0.4 liters/м.п.
                "labor_cost_per_unit": 500,
                "complexity_factor": 1.0
            },
            {
                "name": "Откосы оконные облицовка сендвич-панелями",
                "category": "двери-окна",
                "unit": "м.п.",
                "material_consumption": 0.8,  # 0.8 kg/м.п.
                "labor_cost_per_unit": 700,
                "complexity_factor": 1.1
            },
            {
                "name": "Окна монтаж пластивого подоконника до 2м",
                "category": "двери-окна",
                "unit": "шт.",
                "material_consumption": 1.0,  # 1 kg/unit
                "labor_cost_per_unit": 800,
                "complexity_factor": 1.1
            },
            {
                "name": "Окна монтаж пластивого подоконника более 2m",
                "category": "двери-окна",
                "unit": "шт.",
                "material_consumption": 1.2,  # 1.2 kg/unit
                "labor_cost_per_unit": 1000,
                "complexity_factor": 1.2
            }
        ])       
        await session.execute(insert(MaterialProfiles), [
            {"name": "Грунтовка", "cost_per_unit": 50.0, "category": "Стены"},  # Cost per liter
            {"name": "Штукатурка", "cost_per_unit": 10.0, "category": "Стены"},  # Cost per kg
            {"name": "Краска", "cost_per_unit": 200.0, "category": "Стены"},    # Cost per liter
            {"name": "Плиточный клей", "cost_per_unit": 15.0, "category": "Полы"},  # Cost per kg
            {"name": "Стяжка", "cost_per_unit": 10.0, "category": "Полы"},      # Cost per kg
            {"name": "Гипсокартон", "cost_per_unit": 5.0, "category": "Потолок"},  # Cost per kg
            {"name": "Герметик", "cost_per_unit": 300.0, "category": "Полы"},    # Cost per kg
            {"name": "Пенопласт", "cost_per_unit": 50.0, "category": "Полы"},    # Cost per kg
            {"name": "Линолеум", "cost_per_unit": 10.0, "category": "Полы"},     # Cost per kg
            {"name": "ПВХ панели", "cost_per_unit": 20.0, "category": "Потолок"}, # Cost per kg
        ])

        # Update existing WorkTypes records with material_profile_id
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 3)   # Штукатурка стен по маякам до 30 мм
            .values(material_profile_id=2)  # Штукатурка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 5)   # Грунтование стен (1 слой)
            .values(material_profile_id=1)  # Грунтовка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 6)   # Окрашивание стен водоэмульсионной краской
            .values(material_profile_id=3)  # Краска
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 7)   # Облицовка стен плиткой
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 12)  # Цементная стяжка пола (ЦПС) до 5см
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 13)  # Цементная стяжка пола (ЦПС) до 7см
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 14)  # Стяжка с керамзитом (ЦПС+керамзит) до 10см
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 15)  # Наливные полы из самовыравнивающейся смеси
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 16)  # Наливные полы из самовыравнивающейся смеси объем до 10м²
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 18)  # Укладка пароизоляции, пенофола
            .values(material_profile_id=8)  # Пенопласт
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 19)  # Утепление пола (минвата, пенопласт)
            .values(material_profile_id=8)  # Пенопласт
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 20)  # Монтаж лаг для пола
            .values(material_profile_id=8)  # Пенопласт
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 21)  # Укладка фанеры, ДСП по лагам
            .values(material_profile_id=8)  # Пенопласт
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 23)  # Проклеивание основания под линолеум
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 24)  # Укладка бытового линолеума, ковролина
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 25)  # Укладка полукоммерческого линолеума
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 26)  # Укладка коммерческого линолеума
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 28)  # Укладка кварцвиниловой плитки на клею
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 29)  # Укладка кварцвиниловой плитки с замком
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 30)  # Укладка кафельной плитки со одной из сторон менее 300 мм
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 31)  # Укладка плитки с одной из сторон менее 500 мм
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 32)  # Укладка керамогранита 600х600 мм
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 33)  # Укладка керамогранита 1200х600 мм
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 34)  # Укладка мозаики на пол (в картах)
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 35)  # Укладка шестигранной плитки - соты
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 36)  # Обработка швов ламината, доски герметиком
            .values(material_profile_id=7)  # Герметик
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 37)  # Затирка швов до 600х600 мм цементной затиркой
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 38)  # Затирка швов мозаики и шестигранной цементной затиркой
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 39)  # Затирка швов полимерной затиркой
            .values(material_profile_id=5)  # Стяжка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 41)  # Укладка плитки с декоративными вставками
            .values(material_profile_id=4)  # Плиточный клей
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 42)  # Укладка ламината до 10 мм
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 43)  # Укладка паркетной доски
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 45)  # Переходной порожек металл
            .values(material_profile_id=7)  # Герметик
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 46)  # Переходной порожек ПВХ
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 47)  # Монтаж ПВХ плинтуса
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 48)  # Монтаж плинтус МДФ, дюрополимер
            .values(material_profile_id=9)  # Линолеум
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 50)  # Потолок из гипсокартона одноуровневый в 1 слой
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 51)  # Потолок из гипсокартона одноуровневый в 2 слоя
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 52)  # Потолок из гипсокартона двухуровневый простой
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 53)  # Потолок из гипсокартона двухуровневый сложный
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 55)  # Нанесение грунтовки глубокого проникновения в 1 слой
            .values(material_profile_id=1)  # Грунтовка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 57)  # Выравнивание потолка гипсовой штукатуркой по маякам
            .values(material_profile_id=2)  # Штукатурка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 59)  # Оклейка потолка стеклохолстом, сеткой
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 60)  # Шпатлевание стеклохолста суперфинишем в 1 слой
            .values(material_profile_id=2)  # Штукатурка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 61)  # Покраска потолка в 1 слой
            .values(material_profile_id=3)  # Краска
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 71)  # Потолок из панелей ПВХ по каркасу
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 72)  # Потолок реечный по каркасу
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 73)  # Потолок 'Армстронг' в помещении до 3 м
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 74)  # Монтаж потолка 'Армстронг' в помещении от 3 м
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 75)  # Потолок 'Грильято' в помещении до 3 м
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 76)  # Монтаж потолка 'Грильято' в помещении от 3 м
            .values(material_profile_id=10) # ПВХ панели
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 78)  # Откосы оконные установка примыкающего профиля
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 79)  # Откосы оконные выравнивание под покраску
            .values(material_profile_id=2)  # Штукатурка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 80)  # Откосы оконные оклейка стеклохолстом
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 81)  # Откосы оконные шпатлевание по стеклохолсту
            .values(material_profile_id=2)  # Штукатурка
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 82)  # Откосы оконные покраска в/э краской в 2 слоя
            .values(material_profile_id=3)  # Краска
        )
        await session.execute(
            update(WorkTypes)
            .where(WorkTypes.id == 83)  # Откосы оконные облицовка сендвич-панелями
            .values(material_profile_id=6)  # Гипсокартон
        )
        await session.commit()
    yield
    print("Выключение")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(repairs_router)

@app.get("/", summary="Main")
def root():
    return "Repair Cost Calculator"

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)