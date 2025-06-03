import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import aiofiles
from redis import asyncio as aioredis
import requests
from urllib.parse import urlparse

app = FastAPI(title="FunASR API Server")

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# 音频文件存储目录
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Redis客户端
redis_client = aioredis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)


class AudioRecognitionRequest(BaseModel):
    file: str  # 可以是本地文件路径或URL


class TaskResponse(BaseModel):
    task_id: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


async def download_file(url: str, save_path: str):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        async with aiofiles.open(save_path, 'wb') as f:
            await f.write(response.content)
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")


@app.post("/recognize", response_model=TaskResponse)
async def recognize_audio(request: AudioRecognitionRequest):
    task_id = str(uuid.uuid4())
    file_path = request.file

    if is_valid_url(file_path):
        # 处理URL
        file_name = os.path.basename(urlparse(file_path).path) or f"{task_id}.audio"
        save_path = os.path.join(AUDIO_DIR, file_name)
        await download_file(file_path, save_path)
        file_path = save_path
    elif not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="File not found")

    # 将任务添加到Redis队列
    task_data = {
        "task_id": task_id,
        "file_path": file_path,
        "status": "pending"
    }

    await redis_client.hmset(f"task:{task_id}", task_data)
    await redis_client.lpush("asr_tasks", task_id)

    return TaskResponse(
        task_id=task_id,
        message="Task submitted successfully"
    )


@app.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task_data = await redis_client.hgetall(f"task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(
        task_id=task_id,
        status=task_data.get("status", "unknown"),
        result=task_data.get("result")
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
