import httpx
import time
import random
import string
import threading
import argparse


def generate_random_data(size_mb):
    pairs_count = int(size_mb * 50_000)
    data = {}
    for _ in range(pairs_count):
        key = "".join(random.choices(string.ascii_letters, k=10))
        value = random.randint(1, 1_000_000)
        data[key] = value
    return data


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
    elapsed_time_ms = int(1000 * (time.time() - start_time))
    response.raise_for_status()
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


if __name__ == "__main__":
    main()
