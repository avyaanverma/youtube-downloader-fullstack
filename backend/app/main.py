from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from app.utils import has_ytdlp, select_format, download_video
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CookieItem(BaseModel):
    name: str
    value: str
    domain: str
    path: Optional[str] = "/"
    secure: Optional[bool] = False
    httpOnly: Optional[bool] = False
    expirationDate: Optional[float] = None

class URLRequest(BaseModel):
    url: str
    cookies: Optional[List[CookieItem]] = None

class DownloadRequest(BaseModel):
    url: str
    format_id: str
    cookies: Optional[List[CookieItem]] = None

@app.get('/')
def root():
    return {"message": "YouLaugh API Running"}

@app.get("/check")
def check():
    return {"yt-dlp installed": has_ytdlp()}

@app.post("/formats")
def format(req: URLRequest):
    return {"formats": select_format(req.url, cookies=req.cookies)}

@app.post('/download')
def download(req: DownloadRequest):
    return download_video(req.url, req.format_id, cookies=req.cookies)