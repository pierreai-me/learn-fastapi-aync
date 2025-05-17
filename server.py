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
    elapsed_server: int  # Total time in ms
    profiling: dict[str, int]  # Granular timings in ms


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    return response


def process_request(param, request, endpoint, profiling):
    x_request_id = request.headers.get("x-request-id", "unknown")
    start_time = request.state.start_time

    count = len(param.data)
    maxval = max(param.data.values()) if param.data else 0

    elapsed_server = time.time() - start_time

    result = MyReturnValue(
        name=param.name,
        count=count,
        maxval=maxval,
        elapsed_server=int(1000 * elapsed_server),
        profiling=profiling,
    )

    logger.info(
        f"{x_request_id:13} | return {endpoint} | {elapsed_server:.6f}s {result.model_dump()}"
    )

    return result


@app.post("/ping")
async def ping(param: MyParam, request: Request):
    profiling = {}
    return process_request(param, request, "/ping", profiling)


@app.post("/pong")
async def pong(request: Request):
    x_request_id = request.headers.get("x-request-id", "unknown")
    start_time = request.state.start_time
    profiling = {}
    logger.info(f"{x_request_id:13} | begin /pong")

    chunks = BytesIO()
    n = 0
    async for chunk in request.stream():
        n += 1
        chunks.write(chunk)
    chunks_time = time.time()
    profiling["01_read_chunks"] = int(1000 * (chunks_time - start_time))

    s = chunks.getvalue().decode("utf-8")
    string_time = time.time()
    profiling["02_string_conversion"] = int(1000 * (string_time - chunks_time))

    data_dict = orjson.loads(s)
    json_time = time.time()
    profiling["03_json_parsing"] = int(1000 * (json_time - string_time))

    param = MyParam(**data_dict)
    param_time = time.time()
    profiling["04_param_creation"] = int(1000 * (param_time - json_time))

    return process_request(param, request, "/pong", profiling)