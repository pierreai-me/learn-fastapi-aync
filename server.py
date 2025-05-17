from fastapi import FastAPI, Request
from pydantic import BaseModel
import datetime
import time
import logging
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PID %(process)d] - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)
app = FastAPI()
thread_pool = ThreadPoolExecutor(max_workers=10)


class MyParam(BaseModel):
    name: str
    data: dict[str, int]


class MyReturnValue(BaseModel):
    name: str
    count: int
    maxval: int
    elapsed_server: int  # Time in ms
    request_bytes: int


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    return response


@app.middleware("http")
async def capture_request_size(request: Request, call_next):
    body = await request.body()
    request.state.request_bytes = len(body)
    new_request = Request(
        scope=request.scope,
        receive=request._receive,
        send=request._send,
    )
    response = await call_next(new_request)
    return response


def process_param(body_bytes):
    data_dict = json.loads(body_bytes.decode("utf-8"))
    param = MyParam(**data_dict)
    return param


def process_request(param, request, endpoint):
    start_time = request.state.start_time
    request_bytes = request.state.request_bytes
    x_request_id = request.headers.get("x-request-id", "unknown")

    count = len(param.data)
    maxval = max(param.data.values()) if param.data else 0

    elapsed_server = time.time() - start_time

    result = MyReturnValue(
        name=param.name,
        count=count,
        maxval=maxval,
        elapsed_server=int(1000 * elapsed_server),
        request_bytes=request_bytes,
    )

    logger.info(
        f"{x_request_id:13} | {endpoint:6} | {elapsed_server:.6f}s | {result.model_dump()}"
    )

    return result


@app.post("/ping")
async def ping(param: MyParam, request: Request):
    return process_request(param, request, "/ping")


@app.post("/pong")
async def pong(request: Request):
    body = await request.body()
    loop = asyncio.get_running_loop()
    param = await loop.run_in_executor(thread_pool, process_param, body)
    return process_request(param, request, "/pong")
