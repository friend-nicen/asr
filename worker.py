import os
import typer
import redis
from concurrent.futures import ThreadPoolExecutor
from funasr import AutoModel

app = typer.Typer()

# 配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
MODEL_DIR = "models"
MAX_WORKERS = 2  # 最大并发处理数量

os.environ["MODELSCOPE_CACHE"] = os.path.dirname(os.path.abspath(__file__)) # 设置模型缓存路径

# ffmpeg配置
FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")

# Redis客户端
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)


def download_model():
    """下载模型"""
    try:
        if os.path.exists(MODEL_DIR) and os.listdir(MODEL_DIR):
            print("Model already exists, skipping download...")
            return True

        os.makedirs(MODEL_DIR, exist_ok=True)
        print("Downloading model...")

        # 初始化模型会自动下载
        AutoModel(
            model="paraformer-zh",
            device="cuda" if torch.cuda.is_available() else "cpu",
            ffmpeg_path=FFMPEG_PATH
        )
        return True
    except Exception as e:
        print(f"Error downloading model: {str(e)}")
        return False


def process_audio(task_id: str, file_path: str, model):
    """处理单个音频文件"""
    try:
        # 更新任务状态为处理中
        redis_client.hset(f"task:{task_id}", "status", "processing")

        # 执行语音识别
        result = model.generate(input=file_path)
        text_result = result[0]['text']

        # 更新任务状态和结果
        redis_client.hmset(f"task:{task_id}", {
            "status": "completed",
            "result": text_result
        })

        print(f"Task {task_id} completed successfully")
        return True
    except Exception as e:
        print(f"Error processing task {task_id}: {str(e)}")
        redis_client.hmset(f"task:{task_id}", {
            "status": "failed",
            "result": str(e)
        })
        return False


def start_worker():
    """启动工作进程"""
    print("Initializing ASR model...")
    model = AutoModel(
        model="paraformer-zh",
        model_dir=MODEL_DIR,
        device="cuda" if torch.cuda.is_available() else "cpu",
        ffmpeg_path=FFMPEG_PATH
    )

    print(f"Starting worker with {MAX_WORKERS} concurrent tasks...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            # 从队列中获取任务
            task_id = redis_client.brpop("asr_tasks", timeout=1)
            if task_id is None:
                continue

            task_id = task_id[1]  # brpop returns tuple (queue_name, value)
            task_data = redis_client.hgetall(f"task:{task_id}")

            if not task_data:
                print(f"Task {task_id} not found in Redis")
                continue

            # 提交任务到线程池
            executor.submit(process_audio, task_id, task_data['file_path'], model)


@app.command()
def run(download: bool = typer.Option(False, "--download", "-d", help="Download model before starting worker")):
    """运行ASR工作进程"""
    if download:
        if not download_model():
            print("Failed to download model. Exiting...")
            return

    if not os.path.exists(MODEL_DIR):
        print("Model not found. Please download it first using --download flag")
        return

    start_worker()


if __name__ == "__main__":
    import torch

    app()
