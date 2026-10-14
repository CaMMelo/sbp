from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from blogging.config import settings
from blogging.main import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


def main():
    uvicorn.run(
        "blogging:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
