from datetime import datetime, timedelta
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.crud import (
    create_user,
    get_user_by_email,
    create_link,
    get_link_by_short_code,
    update_link,
    delete_link,
    get_links_by_user,
    get_link_stats,
    increment_link_click,
    get_expired_links,
    delete_expired_links
)
from src.models import User, Link, LinkStats
from src.schemas import UserCreate


def test_create_user():
    db = MagicMock(spec=Session)
    mock_user = User(id=1, email="test@example.com")
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = mock_user

    user_create = UserCreate(email="test@example.com", password="password")
    user = create_user(db, user_create)

    assert user.email == "test@example.com"
    assert db.add.called
    assert db.commit.called
    assert db.refresh.called


def test_get_user_by_email():
    db = MagicMock(spec=Session)
    mock_user = User(email="test@example.com")
    db.query.return_value.filter.return_value.first.return_value = mock_user

    user = get_user_by_email(db, "test@example.com")
    assert user == mock_user


def test_create_link():
    db = MagicMock(spec=Session)
    mock_link = Link(id=1, original_url="http://example.com", short_code="abc123")
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = mock_link

    link = create_link(db, "http://example.com", "abc123")
    assert link.original_url == "http://example.com"
    assert link.short_code == "abc123"
    assert db.add.called
    assert db.commit.called
    assert db.refresh.called


def test_get_link_by_short_code():
    db = MagicMock(spec=Session)
    mock_link = Link(short_code="abc123")
    db.query.return_value.filter.return_value.first.return_value = mock_link

    link = get_link_by_short_code(db, "abc123")
    assert link.short_code == "abc123"


def test_update_link():
    db = MagicMock(spec=Session)
    mock_link = Link(original_url="http://old.com", short_code="old")
    db.query.return_value.filter.return_value.first.return_value = mock_link

    updated_link = update_link(db, "old", "http://new.com", "new")
    assert updated_link.original_url == "http://new.com"
    assert updated_link.short_code == "new"
    assert db.commit.called
    assert db.refresh.called


def test_delete_link():
    db = MagicMock(spec=Session)
    mock_link = Link(short_code="abc123")
    db.query.return_value.filter.return_value.first.return_value = mock_link

    delete_link(db, "abc123")
    assert db.delete.called
    assert db.commit.called


def test_get_links_by_user():
    db = MagicMock(spec=Session)
    mock_links = [Link(user_id=1), Link(user_id=1)]
    db.query.return_value.filter.return_value.all.return_value = mock_links

    links = get_links_by_user(db, 1)
    assert len(links) == 2
    assert all(link.user_id == 1 for link in links)


def test_get_link_stats():
    db = MagicMock(spec=Session)
    mock_link = Link(id=1, original_url="http://example.com")
    mock_stats = LinkStats(clicks=5, last_clicked_at=datetime.now())
    db.query.return_value.filter.return_value.first.side_effect = [mock_link, mock_stats]

    stats = get_link_stats(db, 1)
    assert stats["original_url"] == "http://example.com"
    assert stats["clicks"] == 5


def test_increment_link_click():
    db = MagicMock(spec=Session)
    mock_stats = LinkStats(clicks=0)
    db.query.return_value.filter.return_value.first.return_value = mock_stats

    stats = increment_link_click(db, 1)
    assert stats.clicks == 1
    assert db.commit.called
    assert db.refresh.called


def test_get_expired_links():
    db = MagicMock(spec=Session)
    expired_link = Link(expires_at=datetime.now() - timedelta(days=1))
    db.query.return_value.filter.return_value.all.return_value = [expired_link]

    links = get_expired_links(db)
    assert len(links) == 1


def test_delete_expired_links():
    db = MagicMock(spec=Session)
    expired_link = Link(expires_at=datetime.now() - timedelta(days=1))
    db.query.return_value.filter.return_value.all.return_value = [expired_link]

    deleted = delete_expired_links(db)
    assert len(deleted) == 1
    assert db.delete.called
    assert db.commit.called