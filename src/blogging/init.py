import git

from blogging import models, repository
from blogging.config import settings
from blogging.database import Base, engine


def main():
    repository.clone()

    Base.metadata.create_all(engine)

    repository.sync()

    repo = git.Repo(settings.repository.path)
    origin = repo.remote(name="origin")
    repo.index.add(["db.sqlite"])
    repo.index.commit("blog: init")
    origin.push()
