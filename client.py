import httpx
import time
import datetime
import random
import string
import threading
import argparse


def generate_random_data(size_mb):
    pairs_count = int(size_mb * 40_000)
    data = {}
    for _ in range(pairs_count):
        key = "".join(random.choices(string.ascii_letters, k=10))
        value = random.randint(1, 1_000_000)
        data[key] = value
    return data


def send_request(client, url, name, size_mb):
    data = generate_random_data(size_mb)
    timestamp = datetime.datetime.now()

    payload = {"name": name, "data": data, "timestamp": timestamp.isoformat()}

    start_time = time.time()
    try:
        response = client.post(url, json=payload)
        elapsed = time.time() - start_time
        response_data = response.json()
        print(
            f"Request '{name}' completed in {elapsed:.6f}s. Server processing time: {response_data['elapsed_server']:.6f}s"
        )
        return response_data
    except Exception as e:
        print(f"Error in request '{name}': {e}")
        return None


def periodic_request(url, name, size_mb, interval, duration):
    end_time = time.time() + duration
    with httpx.Client(timeout=120.0) as client:
        while time.time() < end_time:
            send_request(client, url, name, size_mb)
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="FastAPI client for CPU load testing")
    parser.add_argument("--url", type=str, default="http://localhost:8000/ping")
    parser.add_argument("--small-size", type=float, default=0.001)
    parser.add_argument("--large-size", type=float, default=25)
    parser.add_argument("--small-interval", type=float, default=0.1)
    parser.add_argument("--large-interval", type=float, default=1.0)
    parser.add_argument("--duration", type=int, default=60)

    args = parser.parse_args()

    small_thread = threading.Thread(
        target=periodic_request,
        args=(
            args.url,
            "small_request",
            args.small_size,
            args.small_interval,
            args.duration,
        ),
    )
    large_thread = threading.Thread(
        target=periodic_request,
        args=(
            args.url,
            "large_request",
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


if __name__ == "__main__":
    main()
