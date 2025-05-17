# learn-fastapi-aync
Show how a FastAPI server w/ async endpoints handles large requests

## Development

Send the contents of prompt.md to Claude 3.7 w/ extended thinking.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx pydantic gunicorn

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
Request 'small_request' completed in 0.003143s
Request 'large_request' completed in 1.035061s
Request 'small_request' completed in 0.716501s
```

Notice that the last "small_request" took 716 ms to complete vs 3 seconds for the first one.

But not when running 4 workers:

```text
Request 'small' (1060 bytes) completed in 0.033248s
Request 'large' (24861643 bytes) completed in 0.952987s
Request 'small' (1055 bytes) completed in 0.014563s
```