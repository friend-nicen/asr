# FunASR 语音识别服务

这是一个基于 FunASR + Paraformer-zh + FastAPI 实现的语音识别服务，支持异步处理音频文件并返回识别结果。

## 功能特点

- 支持本地音频文件和URL链接的音频识别
- 异步队列处理，支持并发任务
- RESTful API接口
- 自动下载和管理模型
- Redis任务队列

## 系统要求

- Python 3.8+
- Redis服务器
- CUDA（可选，用于GPU加速）

## 安装

1. 克隆项目并安装依赖：

```bash
pip install -r requirements.txt
```

2. 确保Redis服务器已启动

## 配置

主要配置项在 `api_server.py` 和 `worker.py` 中：

- Redis连接配置
- 并发处理数量
- 音频文件存储目录
- 模型存储目录

## 使用方法

1. 启动API服务器：

```bash
python api_server.py
```

2. 首次运行worker时下载模型：

```bash
python worker.py --download
```

3. 启动worker处理服务：

```bash
python worker.py
```

## API接口

### 1. 提交识别任务

```http
POST /recognize
Content-Type: application/json

{
    "file": "path_to_audio_file_or_url"
}
```

响应：
```json
{
    "task_id": "uuid",
    "message": "Task submitted successfully"
}
```

### 2. 查询任务状态

```http
GET /status/{task_id}
```

响应：
```json
{
    "task_id": "uuid",
    "status": "pending|processing|completed|failed",
    "result": "识别结果文本（如果完成）"
}
```

## 注意事项

1. 确保音频文件格式受支持（建议使用wav格式）
2. 保持Redis服务器正常运行
3. 首次运行时需要下载模型，可能需要一些时间
4. 调整MAX_WORKERS参数以适应服务器性能

## 错误处理

- 文件不存在：返回400错误
- URL下载失败：返回400错误
- 任务不存在：返回404错误
- 其他错误：相应的错误信息会记录在任务状态中