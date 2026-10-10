import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path

import git
import sqlalchemy as sa

from blogging.config import settings
from blogging.database import session_factory
from blogging.models import Head, Post

_sync_lock = threading.Lock()


def changed_files(repo, session):
    head = session.get(Head, 1)

    if head is None:
        return [
            ("A", str(path.relative_to(settings.repository.path)), None)
            for path in (settings.repository.path / "public").rglob("*.md")
        ]

    old_commit = repo.commit(head.hash)
    new_commit = repo.head.commit

    diff = old_commit.diff(new_commit)

    return [
        (item.change_type, item.a_path, item.b_path)
        for item in diff
        if any(path and path.startswith("public/") and path.endswith(".md") for path in (item.a_path, item.b_path))
    ]


def has_updates(repo, session):
    head = session.get(Head, 1)
    current_hash = repo.head.commit.hexsha
    return head is None or head.hash != current_hash


def sync_head(repo, session):
    head = session.get(Head, 1)
    current_hash = repo.head.commit.hexsha

    if head is None:
        head = Head(id=1, hash=current_hash)
        session.add(head)
    elif head.hash != current_hash:
        head.hash = current_hash


def create_post(a_path, b_path, session):
    repo = git.Repo(settings.repository.path)
    filepath = settings.repository.path / a_path
    with filepath.open() as f:
        content = f.read().encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
    title = a_path.rsplit("/", 1)[-1].removesuffix(".md")
    post = Post(
        path=a_path,
        title=title,
        created_by=repo.head.commit.author.name,
        updated_by=repo.head.commit.author.name,
        content_hash=content_hash,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(post)


def delete_post(a_path, b_path, session):
    post = session.scalar(sa.select(Post).where(Post.path == a_path))
    session.delete(post)


def update_post(a_path, b_path, session):
    repo = git.Repo(settings.repository.path)
    post = session.scalar(sa.select(Post).where(Post.path == a_path))

    if post is None:
        create_post(a_path, session)
        return

    filepath = settings.repository.path / a_path
    with filepath.open() as f:
        content = f.read()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    post.content = content
    post.content_hash = content_hash
    post.updated_by = repo.head.commit.author.name
    post.updated_at = datetime.now(timezone.utc)


def rename_post(a_path, b_path, session):
    delete_post(a_path, None, session)
    create_post(b_path, None, session)


operation_map = {
    "A": create_post,
    "D": delete_post,
    "M": update_post,
    "R": rename_post,
}


def sync_posts(repo, session):
    changes = changed_files(repo, session)
    for operation, a_path, b_path in changes:
        fn = operation_map.get(operation, lambda ap, bp, s: ...)
        fn(a_path, b_path, session)


def clone():
    git.Repo.clone_from(settings.repository.url, settings.repository.path)


def sync():
    with _sync_lock, session_factory.begin() as session:
        repo = git.Repo(settings.repository.path)
        origin = repo.remote(name="origin")
        origin.pull()

        if has_updates(repo, session):
            sync_posts(repo, session)
            sync_head(repo, session)

            repo.index.add(["db.sqlite"])
            repo.index.commit("blog: update index")
            origin.push()


def get_post(path):
    path = Path("public") / f"{path}.md"
    filepath = settings.repository.path / path

    if not filepath.exists():
        return None

    with filepath.open() as f:
        body = f.read()

    with session_factory.begin() as session:
        post = session.scalar(sa.select(Post).where(Post.path == str(path)))

        return {
            "title": post.title,
            "body": body,
            "created_by": post.created_by,
            "created_at": post.created_at,
        }


def _get_file_tree(path: Path):
    if path.is_file():
        return {"type": "post", "path": str(path.relative_to(settings.repository.path / "public")).removesuffix(".md")}
    return {"type": "directory", "name": path.name, "children": [_get_file_tree(child) for child in path.iterdir()]}


def get_tree():
    return _get_file_tree(settings.repository.path / "public")
