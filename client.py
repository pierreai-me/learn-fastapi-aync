import httpx
import time
import random
import string
import threading
import argparse
import numpy as np


def generate_random_data(size_mb):
    pairs_count = int(size_mb * 50_000)
    data = {}
    for _ in range(pairs_count):
        key = "".join(random.choices(string.ascii_letters, k=10))
        value = random.randint(1, 1_000_000)
        data[key] = value
    return data


# Shared data structure to store elapsed times
request_times = {"small": [], "large": []}


def send_request(base_url, endpoint, name, size_mb, request_counter):
    start_time = time.time()
    data = generate_random_data(size_mb)
    generation_time_ms = int(1000 * (time.time() - start_time))

    url = f"{base_url}{endpoint}"
    request_id = f"{name}-{request_counter:06d}"
    headers = {"x-request-id": request_id}
    payload = {"name": name, "data": data}

    start_time = time.time()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    elapsed_time_ms = int(1000 * (time.time() - start_time))
    request_times[name].append(elapsed_time_ms)

    response_data = response.json()
    print(
        f"{request_id:13} | {endpoint:6} | {response_data['request_bytes']} bytes completed in {elapsed_time_ms} ms, data generation {generation_time_ms} ms"
    )
    return response_data


def periodic_request(base_url, endpoint, name, size_mb, interval, duration):
    end_time = time.time() + duration
    request_counter = 1
    while time.time() < end_time:
        send_request(base_url, endpoint, name, size_mb, request_counter)
        request_counter += 1
        time.sleep(interval)


def calculate_statistics(times):
    if not times:
        return {"count": 0}
    times_array = np.array(times)
    return {
        "count": len(times_array),
        "min": int(float(np.min(times_array))),
        "median": int(float(np.median(times_array))),
        "mean": int(float(np.mean(times_array))),
        "p90": int(float(np.percentile(times_array, 90))),
        "p95": int(float(np.percentile(times_array, 95))),
        "p99": int(float(np.percentile(times_array, 99))),
        "max": int(float(np.max(times_array))),
    }


def main():
    parser = argparse.ArgumentParser(description="FastAPI client for CPU load testing")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument(
        "--endpoint", type=str, default="/ping", choices=["/ping", "/pong"]
    )
    parser.add_argument("--small-size", type=float, default=0.001)
    parser.add_argument("--large-size", type=float, default=25)
    parser.add_argument("--small-interval", type=float, default=0.1)
    parser.add_argument("--large-interval", type=float, default=1.0)
    parser.add_argument("--duration", type=int, default=60)

    args = parser.parse_args()

    print(f"Running tests for {args.duration} seconds on {args.endpoint}...")

    small_thread = threading.Thread(
        target=periodic_request,
        args=(
            args.base_url,
            args.endpoint,
            "small",
            args.small_size,
            args.small_interval,
            args.duration,
        ),
    )
    large_thread = threading.Thread(
        target=periodic_request,
        args=(
            args.base_url,
            args.endpoint,
            "large",
            args.large_size,
            args.large_interval,
            args.duration,
        ),
    )

    small_thread.start()
    large_thread.start()

    small_thread.join()
    large_thread.join()

    print("All requests completed.")

    all_stats = {
        name: calculate_statistics(request_times[name]) for name in ("small", "large")
    }
    print(all_stats)


if __name__ == "__main__":
    main()
