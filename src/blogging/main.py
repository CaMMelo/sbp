import hmac

import markdown
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.background import BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blogging import repository
from blogging.config import settings

router = APIRouter()

if settings.repository.path.is_dir():
    router.mount("/static", StaticFiles(directory=settings.repository.path / "static"), name="static")

templates = Jinja2Templates(directory=settings.repository.path / "templates")
templates.env.filters["markdown"] = lambda text: markdown.markdown(
    text or "",
    extensions=["fenced_code", "tables"],
)


@router.get("/")
def home():
    return "Welcome!"


@router.get("/{path:path}")
def home(request: Request, path: str):
    post = repository.get_post(path)
    if post is None:
        raise HTTPException(status_code=404, detail="Not found")
    context = {"post": post, "tree": repository.get_tree()}
    return templates.TemplateResponse(request=request, name="index.jinja", context=context)


@router.post("/api/sync")
def sync(background_tasks: BackgroundTasks, x_api_token: str = Header(..., alias="X-Api-Token")):
    if not hmac.compare_digest(x_api_token.encode("utf-8"), settings.api.token):
        raise HTTPException(
            status_code=401,
            detail="Invalid API token",
        )

    background_tasks.add_task(repository.sync)
