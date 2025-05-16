from fastapi import FastAPI, Request
from pydantic import BaseModel
import datetime
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True
)
logger = logging.getLogger(__name__)

app = FastAPI()


class MyParam(BaseModel):
    name: str
    data: dict[str, int]
    timestamp: datetime.datetime


class MyReturnValue(BaseModel):
    name: str
    count: int
    maxval: int
    elapsed_server: float  # Time in seconds
    elapsed_from_client: float  # Time in seconds
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

@app.post("/ping")
async def ping(param: MyParam, request: Request):
    start_time = request.state.start_time
    request_bytes = request.state.request_bytes

    count = len(param.data)
    maxval = max(param.data.values()) if param.data else 0

    elapsed_server = time.time() - start_time
    elapsed_from_client = (datetime.datetime.now() - param.timestamp).total_seconds()

    result = MyReturnValue(
        name=param.name,
        count=count,
        maxval=maxval,
        elapsed_server=elapsed_server,
        elapsed_from_client=elapsed_from_client,
        request_bytes=request_bytes,
    )

    logger.info(
        f"Request processed: {result.model_dump()}, Total request time: {elapsed_server:.6f}s"
    )

    return result
