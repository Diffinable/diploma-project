from datetime import timedelta
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import insert, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.repairs import Clients, Estimates, MaterialProfiles, Premises, Users, WorkTypes, estimate_work_types
from src.schemas.repairs import ClientCreate, PremiseCreate, EstimateNoSave, Token, UserCreate, WorkTypeCreate, WorkTypeDetail
from src.database import async_session_factory
from jose import JWTError, jwt
from src.config import settings
from passlib.context import CryptContext

router = APIRouter(prefix="/repairs", tags=["repairs"])

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/repairs/token", auto_error=False)



async def get_async_db():
    async with async_session_factory() as session:
        yield session

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), session: AsyncSession = Depends(get_async_db)):
    if not token:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    user = (await session.execute(select(Users).where(Users.email == email))).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user



def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def calculate_estimate_details(premise: Dict[str, float], work_types: List[WorkTypes], 
    work_type_volumes: List[Dict[str, float]],        
) -> Dict[str, Any]:    
    
    total_material_cost = 0
    total_labor_cost = 0
    work_type_details = []
    if not work_types:
        return {
            "total_labor_cost": 0, 
            "total_material_cost": 0, 
            "total_cost": 0, 
            "work_type_details": [],
        }
    
    area = premise.get("area", 0.0)
    height = premise.get("height", 0.0)


    wall_area = 0.0
    floor_area = 0.0
    perimeter = 0.0
    
    if area > 0 and height > 0:
        side = (area ** 0.5)
        perimeter = 4 * side
        floor_area = area
        wall_area = perimeter * height
        
    volume_map = {wt['id']: wt['volume'] for wt in work_type_volumes}
    for work_type in work_types:
        user_volume = volume_map.get(work_type.id, 0)
        if user_volume <= 0:
            continue 
        labor_cost = user_volume * work_type.labor_cost_per_unit * work_type.complexity_factor
        material_cost = 0
        if work_type.material_profile and work_type.material_consumption:
            material_cost = user_volume * work_type.material_consumption * work_type.material_profile.cost_per_unit
        total_labor_cost += labor_cost
        total_material_cost += material_cost
        work_type_details.append({
            "category": work_type.category,
            "name": work_type.name,
            "units": user_volume,
            "labor_cost": labor_cost,
            "material_cost": material_cost,
            "unit": work_type.unit,
        })
    return {
        "total_labor_cost": total_labor_cost,
        "total_material_cost": total_material_cost,
        "total_cost": total_labor_cost + total_material_cost,
        "work_type_details": work_type_details,
    }

@router.get("/material_profiles")
async def get_material_profiles(session: AsyncSession = Depends(get_async_db)
):
    materials = await session.execute(select(MaterialProfiles)).all()
    return [{"id": m.id, "name": m.name, "cost_per_unit": m.cost_per_unit, "category": m.category} for m in materials]

@router.post("/calculate_estimate")
async def calculate_estimate_nosave(
    request: EstimateNoSave,
    session: AsyncSession = Depends(get_async_db)
):
    if not request.work_types or any(wt.id < 0 for wt in request.work_types):
        raise HTTPException(
            status_code=422,
            detail="work_types must be a non-empty list of objects with positive id and volume"
        )
    
    work_type_ids = [wt.id for wt in request.work_types]
    
    work_types = (await session.execute(
        select(WorkTypes)
        .options(joinedload(WorkTypes.material_profile))
        .where(WorkTypes.id.in_(work_type_ids))
    )).scalars().all()

    if len(work_types) != len(request.work_types):
        raise HTTPException(status_code=404, detail="Some work types not found")

    premise_data = {}
    if request.area is not None and request.height is not None:
        premise_data = {
            "area": request.area,
            "height": request.height,
        }

    calc_details = calculate_estimate_details(premise_data, work_types, [{"id": wt.id, "volume": wt.volume} for wt in request.work_types])

    return {
        "id": None,
        "total_cost": calc_details["total_cost"],
        "total_labor_cost": calc_details["total_labor_cost"],
        "total_material_cost": calc_details["total_material_cost"],
        "work_types": [WorkTypeDetail(**wt) for wt in calc_details["work_type_details"]],
    }

@router.get("/clients")
async def get_clients(user_id: Optional[int] = None, session: AsyncSession = Depends(get_async_db)):
    if user_id:
        clients = (await session.execute(select(Clients).where(Clients.user_id == user_id))).scalars().all()
    else:
        clients = (await session.execute(select(Clients))).scalars().all()
    
    return [{
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "user_id": c.user_id,
    } for c in clients]




@router.post("/register")
async def register_user(
    user: UserCreate, 
    session: AsyncSession = Depends(get_async_db),
):
    existing_user = (
        await session.execute(
            select(Users).where(Users.email == user.email)
        )).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    user_data = {"email": user.email, "hashed_password": hashed_password}
    user_stmt = insert(Users).values(**user_data).returning(Users.id)
    user_result = await session.execute(user_stmt)
    user_id = user_result.scalar_one()

    client_data = {
        "name": user.name, 
        "email": user.email, 
        "user_id": user_id, 
        "phone": None
    }
    client_stmt = insert(Clients).values(**client_data).returning(Clients.id)
    client_result = await session.execute(client_stmt)
    await session.commit()

    return {"message": "User registered successfully"}

@router.post("/token", response_model=Token)
async def login_user(
    email: str = Form(...),
    password: str = Form(...), 
    session: AsyncSession = Depends(get_async_db)
):
    user = (
        await session.execute(select(Users).where(Users.email == email))
    ).scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: Users = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}

@router.get("/my_estimates")
async def get_user_estimates(
    current_user: Users = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_db)
):
    try:
        client = (await session.execute(
            select(Clients).where(Clients.user_id == current_user.id))
        ).scalar_one_or_none()
        if not client:
            return []
        
        estimates = (await session.execute(
            select(Estimates, Premises)
            .join(Premises, Estimates.premise_id == Premises.id)
            .where(Estimates.client_id == client.id)
        )).all()

        result = []
        for estimate, premise in estimates:
            work_types = (await session.execute(
                select(WorkTypes)
                .options(joinedload(WorkTypes.material_profile))
                .join(
                    estimate_work_types, 
                    WorkTypes.id == estimate_work_types.c.work_type_id
                )
                .where(estimate_work_types.c.estimate_id == estimate.id)
            )).scalars().all()

            work_type_volumes = (await session.execute(
                select(estimate_work_types.c.work_type_id, estimate_work_types.c.volume)
                .where(estimate_work_types.c.estimate_id == estimate.id)
            )).all()
            work_type_volumes_dict = [
                {"id": wt_id, "volume": volume} 
                for wt_id, volume in work_type_volumes
            ]

            premise_dict = {
                "area":premise.area,
                "height":premise.height,
            }   

            calc_details = calculate_estimate_details(
                premise_dict,
                work_types, 
                work_type_volumes_dict
            )
            
            result.append({
                    "id": estimate.id,
                    "total_cost": estimate.total_cost,
                    "total_labor_cost": calc_details["total_labor_cost"],
                    "total_material_cost": calc_details["total_material_cost"],
                    "created_at": estimate.created_at,
                    "premise": {
                        "area": premise.area, 
                        "height": premise.height
                    },
                    "work_types": [WorkTypeDetail(**wt) for wt in calc_details["work_type_details"]],
            })
        
        return result
    except Exception as e:
        print(f"Error in get_user_estimates: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )



@router.post("/clients")
async def add_client(client: ClientCreate, session: AsyncSession = Depends(get_async_db)):
    stmt = insert(Clients).values(**client.model_dump())
    result = await session.execute(stmt)
    await session.commit()
    return {"id": result.inserted_primary_key[0]}

@router.post("/premises")
async def add_premise(premise: PremiseCreate, session: AsyncSession = Depends(get_async_db)):
    stmt = insert(Premises).values(**premise.model_dump())
    result = await session.execute(stmt)
    await session.commit()
    return {"id": result.inserted_primary_key[0]}


@router.post("/work_types")
async def add_work_type(work_type: WorkTypeCreate, session: AsyncSession = Depends(get_async_db)):
    stmt = insert(WorkTypes).values(**work_type.model_dump())
    result = await session.execute(stmt)
    await session.commit()
    return {"id": result.inserted_primary_key[0]}

@router.get("/work_types")
async def add_work_type(session: AsyncSession = Depends(get_async_db)):
    work_types = (await session.execute(select(WorkTypes))).scalars().all()
    return [{
        "id": wt.id,
        "name": wt.name,
        "category": wt.category,
        "unit": wt.unit,
        "material_consumption": wt.material_consumption,
        "labor_cost_per_unit": wt.labor_cost_per_unit,
        "complexity_factor": wt.complexity_factor,
        "material_profile_id": wt.material_profile_id,
            "material_cost_per_unit": (
                await session.execute(select(MaterialProfiles.cost_per_unit)
                .filter(MaterialProfiles.id == wt.material_profile_id)                 
            )).scalar_one_or_none()
    } for wt in work_types]

@router.post("/estimates")
async def create_estimate(
    request: EstimateNoSave,
    session: AsyncSession = Depends(get_async_db),
    current_user: Users = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    client = (await session.execute(select(Clients).where(Clients.user_id == current_user.id))).scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="No client associated with user")
    client_id = client.id

    if not request.work_types or any(wt.id <= 0 or wt.volume < 0 for wt in request.work_types):
        raise HTTPException(
            status_code=422, 
            detail="work_types must be a non-empty list of objects with positive id and volume"
        )

    premise_data = {
        "client_id": client_id,
        "area": request.area if request.area is not None else 0,
        "height": request.height if request.height is not None else 0,
    }
    premise_stmt = insert(Premises).values(**premise_data).returning(Premises.id)
    premise_result = await session.execute(premise_stmt)
    premise_id = premise_result.scalar_one()

    work_type_ids = [wt.id for wt in request.work_types]
    work_types_db = []
    if work_type_ids:
        work_types_db = (await session.execute(
            select(WorkTypes)
            .options(joinedload(WorkTypes.material_profile))
            .where(WorkTypes.id.in_(work_type_ids))
        )).scalars().all()

        if len(work_types_db) != len(request.work_types):
            raise HTTPException(status_code=404, detail="Some worktypes not found")

    premise_dict = {
        "area": request.area if request.area is not None else 0,
        "height": request.height if request.height is not None else 0,
    }

    

    calc_details = calculate_estimate_details(
        premise_dict, 
        work_types_db, 
        [{"id": wt.id, "volume": wt.volume} for wt in request.work_types]
    )

    
    estimate_data = {
        "client_id": client_id,
        "premise_id": premise_id,
        "total_cost": calc_details["total_cost"],
        "total_labor_cost": calc_details["total_labor_cost"],
        "total_material_cost": calc_details["total_material_cost"],
    }
    stmt = insert(Estimates).values(**estimate_data)
    result = await session.execute(stmt)    
    estimate_id = result.inserted_primary_key[0]

    work_type_entries = [
        {"estimate_id": estimate_id, "work_type_id": wt.id, "volume": wt.volume }
        for wt in request.work_types
    ]
    if work_type_entries:
        await session.execute(insert(estimate_work_types), work_type_entries)
    await session.commit()
    

    return {
        "id": estimate_id, 
        "total_cost": calc_details["total_cost"], 
        "total_labor_cost": calc_details["total_labor_cost"],
        "total_material_cost": calc_details["total_material_cost"],
        "work_types": [WorkTypeDetail(**wt) for wt in calc_details["work_type_details"]],
    }


