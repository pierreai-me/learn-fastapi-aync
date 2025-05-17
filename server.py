from fastapi import FastAPI, Request
from pydantic import BaseModel
from io import BytesIO
import time
import logging
import orjson
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
    request.state.request_bytes = 0

    async def receive_wrapper():
        message = await request._receive()
        if message["type"] == "http.request":
            request.state.request_bytes += len(message.get("body", b""))
        return message

    request = Request(request.scope, receive_wrapper, request._send)
    response = await call_next(request)
    return response


def process_request(param, request, endpoint):
    x_request_id = request.headers.get("x-request-id", "unknown")
    logger.info(f"{x_request_id:13} | process_request start")

    start_time = request.state.start_time
    request_bytes = request.state.request_bytes

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
        f"{x_request_id:13} | return {endpoint} | {elapsed_server:.6f}s {result.model_dump()}"
    )

    return result


@app.post("/ping")
async def ping(param: MyParam, request: Request):
    return process_request(param, request, "/ping")


@app.post("/pong")
async def pong(request: Request):
    x_request_id = request.headers.get("x-request-id", "unknown")
    logger.info(f"{x_request_id:13} | begin /pong")

    chunks = BytesIO()
    n = 0
    async for chunk in request.stream():
        n += 1
        chunks.write(chunk)
    logger.info(f"{x_request_id:13} | num chunks {n}")

    data_dict = orjson.loads(chunks.getvalue().decode("utf-8"))
    logger.info(f"{x_request_id:13} | loaded json")

    param = MyParam(**data_dict)
    logger.info(f"{x_request_id:13} | created param")

    return process_request(param, request, "/pong")
