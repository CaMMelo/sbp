import git

from sbp import models, repository
from sbp.config import settings
from sbp.database import Base, engine


def main():
    repository.clone()

    Base.metadata.create_all(engine)

    repository.sync()

    repo = git.Repo(settings.repository.path)
    origin = repo.remote(name="origin")
    repo.index.add(["db.sqlite"])
    repo.index.commit("blog: init")
    origin.push()
