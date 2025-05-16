# learn-fastapi-aync
Show how a FastAPI server w/ async endpoints handles large requests

## Development

Send the contents of prompt.md to Claude 3.7 w/ extended thinking.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx pydantic

# shell 1
uvicorn server:app --host 0.0.0.0 --port 8000 --no-access-log

# shell 2
python client.py
```

## Results

As expected, large requests (25 MB) significantly delay small requests:

```text
Request 'small_request' completed in 0.003143s. Server processing time: 0.000681s
Request 'large_request' completed in 1.035061s. Server processing time: 0.766330s
Request 'small_request' completed in 0.716501s. Server processing time: 0.039597s
```

Notice that the last "small_request" took 716 ms to complete vs 3 seconds for the first one.