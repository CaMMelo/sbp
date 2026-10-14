import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path

import git
import sqlalchemy as sa

from blogging.config import settings
from blogging.database import session_factory
from blogging.logs import logger
from blogging.models import Head, Post


def _get_filetree(path: Path):
    if path.is_file():
        return {"type": "file", "path": str(path.relative_to(settings.repository.path / "public")).removesuffix(".md")}
    return {"type": "directory", "name": path.name, "children": [_get_filetree(child) for child in path.iterdir()]}


class Repository:
    def __init__(self):
        self._repo = None
        self._filetree = None

    @property
    def repo(self):
        if self._repo is None:
            self._repo = git.Repo(settings.repository.path)
        return self._repo

    @property
    def filetree(self):
        if self._filetree is None:
            self._filetree = _get_filetree(settings.repository.path / "public")
        return self._filetree

    def __changed_files(self, session):
        head = session.get(Head, 1)

        if head is None:
            return [
                ("A", str(path.relative_to(settings.repository.path)), None)
                for path in (settings.repository.path / "public").rglob("*.md")
            ]

        old_commit = self.repo.commit(head.hash)
        new_commit = self.repo.head.commit

        diff = old_commit.diff(new_commit)

        return [
            (item.change_type, item.a_path, item.b_path)
            for item in diff
            if any(path and path.startswith("public/") and path.endswith(".md") for path in (item.a_path, item.b_path))
        ]

    def __has_updates(self, session):
        head = session.get(Head, 1)
        current_hash = self.repo.head.commit.hexsha
        return head is None or head.hash != current_hash

    def create_post(self, a_path, b_path, session):
        filepath = settings.repository.path / a_path
        with filepath.open() as f:
            content = f.read().encode("utf-8")
            content_hash = hashlib.sha256(content).hexdigest()
        title = a_path.rsplit("/", 1)[-1].removesuffix(".md")
        post = Post(
            path=a_path,
            title=title,
            created_by=self.repo.head.commit.author.name,
            updated_by=self.repo.head.commit.author.name,
            content_hash=content_hash,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(post)

    def delete_post(self, a_path, b_path, session):
        post = session.scalar(sa.select(Post).where(Post.path == a_path))
        session.delete(post)

    def update_post(self, a_path, b_path, session):
        repo = git.Repo(settings.repository.path)
        post = session.scalar(sa.select(Post).where(Post.path == a_path))

        if post is None:
            self.create_post(a_path, session)
            return

        filepath = settings.repository.path / a_path
        with filepath.open() as f:
            content = f.read()
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        post.content = content
        post.content_hash = content_hash
        post.updated_by = repo.head.commit.author.name
        post.updated_at = datetime.now(timezone.utc)

    def rename_post(self, a_path, b_path, session):
        self.delete_post(a_path, None, session)
        self.create_post(b_path, None, session)

    operation_map = {
        "A": create_post,
        "D": delete_post,
        "M": update_post,
        "R": rename_post,
    }

    def sync_head(self, session):
        logger.info("sync head started")
        head = session.get(Head, 1)
        current_hash = self.repo.head.commit.hexsha

        if head is None:
            head = Head(id=1, hash=current_hash)
            session.add(head)
        elif head.hash != current_hash:
            head.hash = current_hash
        logger.info("sync head finished")

    def sync_posts(self, session):
        logger.info("sync posts started")
        changes = self.__changed_files(session)
        for operation, a_path, b_path in changes:
            fn = self.operation_map.get(operation, lambda ap, bp, s: ...)
            fn(self, a_path, b_path, session)
        logger.info("sync posts finished")

    def sync_filetree(self):
        logger.info("sync filetree started")
        self._filetree = _get_filetree(settings.repository.path / "public")
        logger.info("sync filetree finished")

    def sync(self):
        logger.info("sync started")
        with session_factory.begin() as session:
            origin = self.repo.remote(name="origin")
            origin.pull()

            if self.__has_updates(session):
                self.sync_posts(session)
                self.sync_head(session)
                self.sync_filetree()

        logger.info("commit db.sqlite")
        self.repo.index.add(["db.sqlite"])
        self.repo.index.commit("blog: sync")
        origin.push()

        logger.info("sync finished")

    def get_post(self, path):
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

    def get_readme(self):
        filepath = settings.repository.path / "README.md"

        if not filepath.exists():
            return None

        with filepath.open() as f:
            body = f.read()

        return {
            "body": body,
        }


_instance = Repository()
_sync_lock = threading.Lock()


def clone():
    git.Repo.clone_from(settings.repository.url, settings.repository.path)


def get_readme():
    return _instance.get_readme()


def get_tree():
    return _instance.filetree


def get_post(path):
    return _instance.get_post(path)


def sync():
    with _sync_lock:
        return _instance.sync()
