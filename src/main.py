import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.auth import get_current_user, create_access_token, authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES
from src.crud import create_user, get_user_by_email, create_link, get_link_by_short_code, update_link, delete_link, \
    get_links_by_user, get_link_by_original_url, get_link_stats, increment_link_click, get_expired_links, \
    delete_expired_links
from src.database import SessionLocal, engine
from src.models import Base, User
from src.redis_cache import redis_cache, cache_invalidate
from src.schemas import UserCreate, UserOut, LinkCreate, LinkOut, LinkStatsOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register", response_model=UserOut)
def register_user(user: UserCreate, db=Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db=db, user=user)


@app.post("/token")
def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db=Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/links/shorten", response_model=LinkOut)
def create_short_link(
        link: LinkCreate,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user),
        db=Depends(get_db)
):
    if link.custom_alias:
        db_link = get_link_by_short_code(db, link.custom_alias)
        if db_link:
            raise HTTPException(status_code=400, detail="Custom alias already in use")
        short_code = link.custom_alias
    else:
        short_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
        while get_link_by_short_code(db, short_code):
            short_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))

    db_link = create_link(
        db=db,
        original_url=link.original_url,
        short_code=short_code,
        expires_at=link.expires_at,
        user_id=current_user.id if current_user else None
    )

    base_url = str(request.base_url)
    db_link.short_url = f"{base_url}{short_code}"

    return db_link


@app.get("/{short_code}")
@redis_cache(expire=60)
async def redirect_to_original(
        short_code: str,
        db=Depends(get_db)
):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")

    if db_link.expires_at and db_link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link has expired")

    increment_link_click(db, db_link.id)

    return RedirectResponse(url=db_link.original_url)


@app.delete("/links/{short_code}")
@cache_invalidate(pattern="*")
async def delete_short_link(
        short_code: str,
        current_user: User = Depends(get_current_user),
        db=Depends(get_db)
):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")

    if db_link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")

    delete_link(db, short_code)
    return {"message": "Link deleted successfully"}


@app.put("/links/{short_code}", response_model=LinkOut)
@cache_invalidate(pattern="*")
def update_short_link(
    short_code: str,
    link: LinkCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")

    if db_link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")

    if link.custom_alias and link.custom_alias != short_code:
        existing_link = get_link_by_short_code(db, link.custom_alias)
        if existing_link:
            raise HTTPException(status_code=400, detail="Custom alias already in use")

    original_url = str(link.original_url) if hasattr(link.original_url, '__str__') else link.original_url

    updated_link = update_link(
        db=db,
        short_code=short_code,
        original_url=original_url,
        new_short_code=link.custom_alias,
        expires_at=link.expires_at
    )

    return LinkOut.from_orm(updated_link)


@app.get("/links/{short_code}/stats", response_model=LinkStatsOut)
def get_link_statistics(short_code: str, db=Depends(get_db)):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")

    stats = get_link_stats(db, db_link.id)
    return stats


@app.get("/links/search")
def search_link_by_original_url(original_url: str, db=Depends(get_db)):
    db_link = get_link_by_original_url(db, original_url)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    return db_link


@app.get("/users/me/links", response_model=List[LinkOut])
def get_user_links(
        current_user: User = Depends(get_current_user),
        db=Depends(get_db)
):
    return get_links_by_user(db, current_user.id)


@app.delete("/links/cleanup/expired")
def cleanup_expired_links(db=Depends(get_db)):
    expired_links = get_expired_links(db)
    delete_expired_links(db)
    return {"message": f"Deleted {len(expired_links)} expired links"}


@app.get("/links/expired/history", response_model=List[LinkOut])
def get_expired_links_history(db=Depends(get_db)):
    return get_expired_links(db)
