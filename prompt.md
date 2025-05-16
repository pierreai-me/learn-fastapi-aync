Goal: Understand how CPU-intensive string manipulation and object creation are in Python.

Method:

1. A FastAPI async server with a single GET endpoint /ping, that accepts a parameter of the following type:

```py
class MyParam(BaseModel):
    name: str
    data: dict[str, int]
    timestamp: datetime.datetime
```

and returns:

```py
class MyReturnValue(BaseModel):
    name: str  # same name as in MyParam
    count: int  # number of entries in `MyParam.data`
    maxval: int  # maximum value across `MyParam.data.values()`
    elapsed_server: datetime.timeinterval  # see (a) below
    elapsed_from_client: datetime.timeinterval
```

The only logging should be when the server returns a response, it logs the return value along with the total request time in two ways: (a) using a timer it starts at the beginning of the request and (b) using `MyParam.timestamp`.

2. A client script that uses multithreading httpx and sends requests to the /ping endpoint. It sends two three of requests. (a) every 0.1 second, it sends a small request (say about 10 elements in data, made of short strings and small integers). (b) every 0.5 second, it sends a large request of about 5 MB. (c) every 1.0 second, it sends an even larger request of about 25 MB. Make all those parameters configurable. Use httpx as the http client library.

Provide the following:
1. The server code as one Python file
2. The client code as one Python file
3. Instructions on how to create the venv, pip install packages, and run the server.

My intuition is that having to process large requests of 25 MB will slow down the other requests. That would be a sign that these string operations and object constructions are CPU-intensive operations when the objects are large, and therefore one should use multithreading instead of asyncio in their FastAPI server.