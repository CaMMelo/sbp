from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from sbp.config import settings
from sbp.main import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


def main():
    uvicorn.run(
        "sbp:app",
        host="0.0.0.0",
        port=settings.server.port,
        reload=settings.server.reload,
    )
