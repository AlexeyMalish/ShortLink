from sqlalchemy.orm import Session
from datetime import datetime

from src import models, schemas, auth


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_link(db: Session, original_url: str, short_code: str, expires_at: datetime = None, user_id: int = None):
    if hasattr(original_url, '__str__'):
        original_url = str(original_url)

    db_link = models.Link(
        original_url=original_url,
        short_code=short_code,
        expires_at=expires_at,
        user_id=user_id
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link


def get_link_by_short_code(db: Session, short_code: str):
    return db.query(models.Link).filter(models.Link.short_code == short_code).first()


def get_link_by_original_url(db: Session, original_url: str):
    return db.query(models.Link).filter(models.Link.original_url == original_url).first()


def update_link(
        db: Session,
        short_code: str,
        original_url: str,
        new_short_code: str = None,
        expires_at: datetime = None
):
    db_link = get_link_by_short_code(db, short_code)
    if db_link:
        if hasattr(original_url, '__str__'):
            db_link.original_url = str(original_url)
        else:
            db_link.original_url = original_url

        if new_short_code:
            db_link.short_code = new_short_code
        if expires_at:
            db_link.expires_at = expires_at
        db.commit()
        db.refresh(db_link)
    return db_link


def delete_link(db: Session, short_code: str):
    db_link = get_link_by_short_code(db, short_code)
    if db_link:
        db.delete(db_link)
        db.commit()
    return db_link


def get_links_by_user(db: Session, user_id: int):
    return db.query(models.Link).filter(models.Link.user_id == user_id).all()


def get_link_stats(db: Session, link_id: int):
    link = db.query(models.Link).filter(models.Link.id == link_id).first()
    stats = db.query(models.LinkStats).filter(models.LinkStats.link_id == link_id).first()

    return {
        "original_url": link.original_url,
        "created_at": link.created_at,
        "clicks": stats.clicks if stats else 0,
        "last_clicked_at": stats.last_clicked_at if stats else None
    }


def increment_link_click(db: Session, link_id: int):
    stats = db.query(models.LinkStats).filter(models.LinkStats.link_id == link_id).first()
    if stats:
        stats.clicks += 1
        stats.last_clicked_at = datetime.utcnow()
        db.commit()
        db.refresh(stats)
    return stats


def get_expired_links(db: Session):
    return db.query(models.Link).filter(models.Link.expires_at < datetime.utcnow()).all()


def delete_expired_links(db: Session):
    expired_links = get_expired_links(db)
    for link in expired_links:
        db.delete(link)
    db.commit()
    return expired_links