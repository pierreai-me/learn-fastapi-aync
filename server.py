from fastapi import FastAPI, Request
from pydantic import BaseModel
from io import BytesIO
import time
import logging
import orjson
from concurrent.futures import ThreadPoolExecutor
import time
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PID %(process)d] - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)
app = FastAPI()
thread_pool = ThreadPoolExecutor(max_workers=10)


class Profiler:
    def __init__(self):
        self.timings = {}
        self._index = 0

    @contextmanager
    def measure(self, name):
        start = time.perf_counter()
        try:
            yield
        finally:
            self._index += 1
            indexed_name = f"{self._index:03d}_{name}"
            self.timings[indexed_name] = int(1000 * (time.perf_counter() - start))


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
    profiling = {}
    logger.info(f"{x_request_id:13} | begin /pong")

    profiler = Profiler()

    with profiler.measure("read_chunks"):
        chunks = BytesIO()
        n = 0
        async for chunk in request.stream():
            n += 1
            chunks.write(chunk)

    with profiler.measure("string_conversion"):
        s = chunks.getvalue().decode("utf-8")

    with profiler.measure("json_parsing"):
        data_dict = orjson.loads(s)

    with profiler.measure("param_creation"):
        param = MyParam(**data_dict)

    return process_request(param, request, "/pong", profiler.timings)
