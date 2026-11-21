import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from campus.controllers import router
from campus.auth import router as auth_router


load_dotenv()
app = FastAPI(title="Campus Viva API", version="1.0.0")
origins = [v.strip().rstrip("/") for v in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if v.strip()]
app.add_middleware(CORSMiddleware, allow_origins=[o for o in origins if o != "*"],
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"], allow_credentials=True)
app.include_router(router)
app.include_router(auth_router)


@app.middleware("http")
async def no_stale_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def root():
    return {"name": "Campus Viva API", "docs": "/docs"}


@app.exception_handler(PyMongoError)
@app.exception_handler(RuntimeError)
async def storage_unavailable(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={"detail": "Armazenamento indisponível. Verifique a configuração do servidor."})
