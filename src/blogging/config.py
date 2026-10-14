from pathlib import Path

from dynaconf import Dynaconf
from dynaconf.validator import Validator

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["settings.toml", ".secrets.toml"],
    validators=[
        Validator("repository.url", must_exist=True, ne=None),
        Validator("repository.path", default="blog", cast=Path),
        Validator("api.token", must_exist=True, cast=lambda x: str.encode(x, "utf-8")),
        Validator("server.port", default=8080),
    ],
)
