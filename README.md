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

# shell 2
python client.py
```

## Results

As expected, large requests (25 MB) significantly delay small requests when running a single worker:

```text
# /ping (BaseModel) -> slow (check out p95)
python client.py --endpoint /ping --duration 100

    {
        'small': {'count': 534, 'min': 15, 'median': 40, 'mean': 79, 'p90': 72, 'p95': 658, 'p99': 858, 'max': 948},
        'large': {'count': 28, 'min': 948, 'median': 1055, 'mean': 1071, 'p90': 1175, 'p95': 1204, 'p99': 1234, 'max': 1246}
    }

# /pong (Request, orjson, read body in chunks) -> faster but still delays
python client.py --endpoint /pong --duration 100

    {
        'small': {'count': 594, 'min': 15, 'median': 41, 'mean': 59, 'p90': 71, 'p95': 367, 'p99': 423, 'max': 457},
        'large': {'count': 31, 'min': 651, 'median': 689, 'mean': 695, 'p90': 736, 'p95': 744, 'p99': 752, 'max': 754}
    }
```

Using 4 workers solves the issue for small requests w/o the need for additional improvements (check out p95). NOTE - This is using a **new** httpx client on every call.

```text
python client.py --endpoint /ping --duration 100

    {
        'small': {'count': 703, 'min': 15, 'median': 20, 'mean': 35, 'p90': 66, 'p95': 73, 'p99': 199, 'max': 459},
        'large': {'count': 28, 'min': 1039, 'median': 1098, 'mean': 1120, 'p90': 1189, 'p95': 1229, 'p99': 1264, 'max': 1270}
    }

python client.py --endpoint /pong --duration 100

    {
        'small': {'count': 695, 'min': 15, 'median': 22, 'mean': 35, 'p90': 65, 'p95': 69, 'p99': 80, 'max': 585},
        'large': {'count': 31, 'min': 691, 'median': 745, 'mean': 749, 'p90': 788, 'p95': 799, 'p99': 801, 'max': 802}
    }
```