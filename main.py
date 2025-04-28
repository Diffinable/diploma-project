from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends, Response, BackgroundTasks, Query, Body, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
# from fastapi.openapi.docs import get_swagger_ui_html
import asyncio
import time
import uvicorn
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from authx import AuthX, AuthXConfig

app = FastAPI()




engine = create_async_engine('sqlite+aiosqlite:///books.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

config = AuthXConfig()
config.JWT_SECRET_KEY = "SECRET_KEY"
config.JWT_ACCESS_COOKIE_NAME = "my_access_token"
config.JWT_TOKEN_LOCATION = ["cookies"]

security = AuthX(config=config)

class UserLoginSchema(BaseModel):
    username: str
    password: str

def sync_task():
    time.sleep(3)
    print("Отправлен email")

async def async_task():
    await asyncio.sleep(3)
    print("Сделан запрос в сторонний API")

    

async def get_session():
    async with new_session() as session:
        yield session



SessionDep = Annotated[AsyncSession, Depends(get_session)]

class Base(DeclarativeBase):
    pass

class BookModel(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author: Mapped[str]

class BookAddSchema(BaseModel):
    title: str
    author: str

class NewBook(BaseModel):
    title: str
    author: str

class UserSchema(BaseModel):
    email: EmailStr
    bio: str | None = Field(max_length=10)

class UserAgeSchema(UserSchema):
    age: int = Field(ge=0, le=130)
    model_config = ConfigDict(extra="forbid")

class BookSchema(BookAddSchema):
    id: int

hotels = [
    {"id": 1, "title": "Сочи", "name": "Sochi"},
    {"id": 2, "title": "Дубай", "name": "Dubai"},
]

books = [
    {
        "id": 1,
        "title": "Асинхронность в Python",
        "author": "Мэтью",
    },
    {
        "id": 2,
        "title": "Backend разработка в python",
        "author": "Артем",
    }, 
]

data = {
    "email": "nau@mail.ru",
    "bio": "im bro",
    "age": 11,
}
data_wo_age = {
    "email": "nau@mail.ru",
    "bio": "female",
}

users = []


@app.get("/get_users", tags=["Пользователи"], summary="Получить пользователей")
async def get_users():
    return [{"id": 1, "name": "Artem"}]

@app.get("/sync_func/{id}")
def sync_func(id: int):
    print(f"sync. Начал {id}: {time.time():.2f}")
    time.sleep(3)
    print(f"sync. Закончил {id}: {time.time():.2f}")

@app.get("/async_func/{id}")
async def sync_func(id: int):
    print(f"async. Начал {id}: {time.time():.2f}")
    await asyncio.sleep(3)
    print(f"async. Закончил {id}: {time.time():.2f}")
    

@app.get("/hotels")
def get_hotels(
    id: int | None = Query(None, description="Id"),
    title: str | None = Query(None, description="Name of hotel")
):
    hotels_ = []
    for hotel in hotels:
        if id and hotel["id"] != id:
            continue
        if title and hotel["title"] != title:
            continue
        hotels_.append(hotel)
    return hotels_

@app.post("/files")
async def upload_file(uploaded_file: UploadFile):
    file = uploaded_file.file
    filename = uploaded_file.filename
    with open(f"1_{filename}", "wb") as f:
        f.write(file.read())

@app.post("/multiple_files")
async def upload_files(uploaded_files: list[UploadFile]):
    for uploaded_file in uploaded_files:
        file = uploaded_file.file
        filename = uploaded_file.filename
        with open(f"1_{filename}", "wb") as f:
            f.write(file.read())

@app.get("/files/{filename}")
async def get_file(filename: str):
    return FileResponse(filename)

def iterfile(filename: str):
    with open(filename, "rb") as file:
        while chunk := file.read(1024 * 1024):
            yield chunk
    
    

@app.get("/files/streaming/{filename}")
async def get_streaming_file(filename: str):
    return StreamingResponse(iterfile(filename), media_type="video/mp4")

@app.post("/hotels")
def create_hotel(
    title: str = Body(embed=True),
):
    global hotels
    hotels.append({
        "id": hotels[-1]["id"] + 1,
        "title": title
    })
    return {"status": "OK"}



@app.put("/hotels/{hotel_id}")
def edit_hotel(
    hotel_id: int,
    title: str = Body(),
    name: str = Body(),
):
    global hotels
    hotel = [hotel for hotel in hotels if hotel["id"] == hotel_id][0]
    hotel["title"] = title
    hotel["name"] = name
    return {"status": "OK"}

@app.patch(
        "/hotels/{hotel_id}",
        summary="Частичное обновление данных об отеле",
        description="<h1>Тут мы частично обновляем данные об отеле"
)
def partially_edit_hotel(
    hotel_id: int,
    title: str | None = Body(None),
    name: str | None = Body(None),
):
    global hotels
    hotel = [hotel for hotel in hotels if hotel["id"] == hotel_id][0]
    if title:
        hotel["title"] = title
    if name:
        hotel["name"] = name
    return {"status": "OK"}

@app.get("/hotels/{hotel_id}")
def delete_hotel(hotel_id: int):
    global hotels
    hotels = [hotel for hotel in hotels if hotel["id"] != hotel_id]
    return {"status": "OK"}






@app.post("/login")
def login(creds: UserLoginSchema, response: Response):
    if creds.username == "test" and creds.password == "test":
        token = security.create_access_token(uid="12345")
        response.set_cookie(config.JWT_ACCESS_COOKIE_NAME, token)
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Incorrect username or password")
        



@app.post("/setup_database")
async def startup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"ok": True}

@app.post("/sync_task")
def start_sync_task():
    sync_task()
    return {"ok": True}

@app.post("/async_task")
async def start_async_task():
    await async_task()
    return {"ok": True}

@app.post("/corutine_task")
async def start_corutine_task():
    asyncio.create_task(async_task())
    return {"ok": True}

@app.post("/bg_tasks")
async def start_bg_task(bg_tasks: BackgroundTasks):
    bg_tasks.add_task(sync_task)    
    return {"ok": True}

@app.get("/protected", dependencies=[Depends(security.access_token_required)])
def protected():
    return {"data": "Top Secret"}



@app.post("/add_book")
async def add_book(data: BookAddSchema, session: SessionDep):
    new_book = BookModel(
        title=data.title,
        author=data.author
    )
    session.add(new_book)
    await session.commit()
    return {"ok": True}

@app.get("/get_book")
async def get_book(sesison: SessionDep):
    query = select(BookModel)
    result = await sesison.execute(query)
    return result.scalars().all()


@app.post("/books")
def create_book(new_book: NewBook):
    books.append({
        "id": len(books) + 1,
        "title": new_book.title,
        "author": new_book.author,
    })
    return {"succes": True, "message": "Книга успешно добавлена"}



user = UserAgeSchema(**data)
user1 = UserSchema(**data_wo_age)
print(repr(user))
print(repr(user1))


@app.post("/users")
def add_user(user1: UserSchema):
    users.append(user1)
    return {"ok": True, "msg": "User added"}

@app.get("/users") 
def add_user() -> list[UserSchema]:    
    return users






def func(data_: dict):
    data_["age"] += 1


@app.get(
        "/books",
        tags=["Книги"],
        summary="Получить все книги"
)
def read_books():
    return books

@app.get("/books/{book_id}", 
         tags=["Книги"],
         summary="Получить конкретную книгу")
def get_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
        
    raise HTTPException(status_code=404, detail="Книга не найдена")


@app.get("/", summary="Главная")
def root():
    return "Hello world"


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)
      