# learn-fastapi-aync
Show how a FastAPI server w/ async endpoints handles large requests

## Development

Send the contents of prompt.md to Claude 3.7 w/ extended thinking.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx pydantic gunicorn orjson numpy

# shell 1 - run one of the following commands
# single worker
uvicorn server:app --host 0.0.0.0 --port 8000 --no-access-log
# multiple workers, less busy worker gets connection
gunicorn -w 4 -k uvicorn.workers.UvicornWorker --reuse-port server:app

# shell 2 - run one of the following commands (see Summary for a discussion of the endpoints)
python client.py --endpoint /ping --duration 100
python client.py --endpoint /pong --duration 100
```

## Results

### Summary

As expected, large requests (25 MB) significantly delay small requests when running a single worker.
Using 4 workers solves the issue for small requests w/o the need for additional improvements (check out p95).
NOTE - This is using a **new** httpx client on every call.

The two endpoints are:
- `/ping`: BaseModel
- `/pong`: Request + orjson + read body in chunks

| Request Size | Workers  | Endpoint | Count | Min | Median | Mean | p90  | p95  | p99  | Max  |
|--------------|----------|----------|-------|-----|--------|------|------|------|------|------|
| Small        | Single   | /ping    | 534   | 15  | 40     | 79   | 72   | 658  | 858  | 948  |
| Small        | Single   | /pong    | 594   | 15  | 41     | 59   | 71   | 367  | 423  | 457  |
| Small        | Multiple | /ping    | 703   | 15  | 20     | 35   | 66   | 73   | 199  | 459  |
| Small        | Multiple | /pong    | 695   | 15  | 22     | 35   | 65   | 69   | 80   | 585  |
| Large        | Single   | /ping    | 28    | 948 | 1055   | 1071 | 1175 | 1204 | 1234 | 1246 |
| Large        | Single   | /pong    | 31    | 651 | 689    | 695  | 736  | 744  | 752  | 754  |
| Large        | Multiple | /ping    | 28    | 1039| 1098   | 1120 | 1189 | 1229 | 1264 | 1270 |
| Large        | Multiple | /pong    | 31    | 691 | 745    | 749  | 788  | 799  | 801  | 802  |

### Runs

```text
# Single worker, /ping
{
    'small': {'count': 534, 'min': 15, 'median': 40, 'mean': 79, 'p90': 72, 'p95': 658, 'p99': 858, 'max': 948},
    'large': {'count': 28, 'min': 948, 'median': 1055, 'mean': 1071, 'p90': 1175, 'p95': 1204, 'p99': 1234, 'max': 1246}
}

# Single worker, /pong
{
    'small': {'count': 594, 'min': 15, 'median': 41, 'mean': 59, 'p90': 71, 'p95': 367, 'p99': 423, 'max': 457},
    'large': {'count': 31, 'min': 651, 'median': 689, 'mean': 695, 'p90': 736, 'p95': 744, 'p99': 752, 'max': 754}
}

# 4 workers, /ping
{
    'small': {'count': 703, 'min': 15, 'median': 20, 'mean': 35, 'p90': 66, 'p95': 73, 'p99': 199, 'max': 459},
    'large': {'count': 28, 'min': 1039, 'median': 1098, 'mean': 1120, 'p90': 1189, 'p95': 1229, 'p99': 1264, 'max': 1270}
}

# 4 workers, /pong
{
    'small': {'count': 695, 'min': 15, 'median': 22, 'mean': 35, 'p90': 65, 'p95': 69, 'p99': 80, 'max': 585},
    'large': {'count': 31, 'min': 691, 'median': 745, 'mean': 749, 'p90': 788, 'p95': 799, 'p99': 801, 'max': 802}
}
```

## Discussion

The problems we're facing are:
1. When a coroutine performs CPU-heavy computations w/o any `await` statement, it does not release the single-threaded event loop. **All requests are blocked during that time.**
2. Python has a GIL (Global Interpreter Lock). Some libraries like `json` only infrequently release the GIL. Even when running multiple threads, if a thread doesn't release the GIL, other threads can't run.
    - Since 3.13 there's work to remove it but it's currently an [optional build](https://docs.python.org/3/howto/free-threading-python.html)
3. Very large requests (>1MB) incur signficant processing costs:
    - Conversions between bytes and strings
    - Creation of primitive types through JSON loading
    - Creation of user defined types (e.g. BaseModel)
    - Logging of such objects

Discussion of possible solutions:
- Define FastAPI endpoints as synchronous instead of asynchronous (i.e. drop the `async def` in favor of `def`).
  This forces FastAPI to allocate a pool of about 40 threads to the application.
  No event loops are used.
  This would solve the first issue (no longer holding an event loop for extended periods of time).
  However the second issue is still there (not releasing the GIL).
- Use more BPaaS pods.
  Most small requests would no longer be delayed by large requests.
  However some small requests may still be impacted, depending on how BPaaS routes requests (balances the load) among all the pods.
- Use multiple workers, as we have done here.
  Small requests are no longer delayed by large requests.
  We need to check how keep alive connections are handled.
  If clients A and B always use the same worker, and client A sends a large request, client B will be impacted.
  There are ways to disallow keep alive connections from the server side.
  The question is - what is the latency penalty for clients?

In effect there are two categories of problems: small requests being starved, and large requests taking a long time to complete. The previous solutions try to address starvation. To help large requests take a shorter amount of time to complete, we need to instrument or profile our code, clarify which use cases we want to support or not, and work on things like using faster JSON parsers, stop logging very long strings, etc., based on the results of that profiling.

For instance here's /pong spends most of the time processing a large request:

```text
{'01_read_chunks': 19, '02_string_conversion': 10, '03_json_parsing': 252, '04_param_creation': 153}
```

i.e. parsing a JSON-encoded string and creating a BaseModel object.

Also:
- Discuss with teams to avoid large requests in the short term
- Collect statistics on request size per user
