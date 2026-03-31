from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.utils import select_format, download_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestModel(BaseModel):
    url: str
    format_id: str | None = None
    cookies: str | None = None


@app.get("/")
def root():
    return {"message": "API running"}


@app.post("/formats")
def formats(req: RequestModel):
    return {"formats": select_format(req.url, req.cookies)}


@app.post("/download")
def download(req: RequestModel):
    return download_video(req.url, req.format_id, req.cookies)