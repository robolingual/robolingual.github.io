"""アップロードされた曲をファンコットリミックスに変換して返すAPIサーバー。

使い方:
    uvicorn app:app --reload
"""
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pipeline import run

app = FastAPI(title="Indoneshizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/remix")
async def remix(file: UploadFile = File(...), bpm: float = Form(160.0)) -> FileResponse:
    work_dir = Path(tempfile.mkdtemp())
    input_path = work_dir / file.filename
    out_path = work_dir / "remix.wav"

    with input_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    run(str(input_path), bpm, str(out_path))

    return FileResponse(out_path, media_type="audio/wav", filename="indoneshizer_remix.wav")
