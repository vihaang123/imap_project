"""Benchmark the three APOD endpoints and demo invalidation.

Run the server first (python manage.py runserver), then:
    python scripts/benchmark.py --date 2024-01-15

Kept deliberately small so we respect NASA's rate limit (DEMO_KEY allows about
30 requests/hour per IP). Total NASA calls: 3 uncached + 1 low-level miss
+ 1 page-cache miss + 1 after invalidation = about 6. The remaining requests
hit our own server's Redis cache, never NASA. Do NOT raise --hits into the
thousands and never point this at NASA directly.
"""
import argparse
import json
import statistics
import time

import requests


def timed_get(url, **params):
    start = time.perf_counter()
    r = requests.get(url, params=params, timeout=30)
    ms = (time.perf_counter() - start) * 1000
    return r, ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000/api")
    ap.add_argument("--date", default="2024-01-15")
    ap.add_argument("--hits", type=int, default=20)
    args = ap.parse_args()
    base, d = args.base, args.date

    requests.post(f"{base}/cache/invalidate/")  # start from a cold cache

    results = {}

    # 1. uncached baseline (calls NASA every time)
    times = []
    for _ in range(3):
        r, ms = timed_get(f"{base}/apod/uncached/", date=d)
        r.raise_for_status()
        times.append(ms)
    results["uncached (avg of 3)"] = statistics.mean(times)

    # 2. low-level cache: 1 miss then N hits
    r, ms = timed_get(f"{base}/apod/low-level/", date=d)
    r.raise_for_status()
    assert r.headers["X-Cache"] == "MISS", r.headers
    results["low-level MISS"] = ms
    times = []
    for _ in range(args.hits):
        r, ms = timed_get(f"{base}/apod/low-level/", date=d)
        assert r.headers["X-Cache"] == "HIT"
        times.append(ms)
    results[f"low-level HIT (avg of {args.hits})"] = statistics.mean(times)

    # 3. per-view cache
    r, ms = timed_get(f"{base}/apod/page-cached/", date=d)
    r.raise_for_status()
    results["page-cache MISS"] = ms
    times = [timed_get(f"{base}/apod/page-cached/", date=d)[1] for _ in range(args.hits)]
    results[f"page-cache HIT (avg of {args.hits})"] = statistics.mean(times)

    # 4. invalidation demo: change the source, next request must be fresh
    before, _ = timed_get(f"{base}/apod/low-level/", date=d)
    requests.post(
        f"{base}/override/",
        json={"date": d, "title": "EDITED BY BENCHMARK", "note": "invalidation demo"},
    )
    after, ms = timed_get(f"{base}/apod/low-level/", date=d)
    results["after invalidation (fresh MISS)"] = ms
    print("\nInvalidation check")
    print("  title before :", before.json()["title"], "|", before.headers["X-Cache"])
    print("  title after  :", after.json()["title"], "|", after.headers["X-Cache"])
    assert after.headers["X-Cache"] == "MISS"
    assert after.json()["title"] == "EDITED BY BENCHMARK"

    print("\nResponse times")
    print(f"{'scenario':<38}{'ms':>10}")
    for name, v in results.items():
        print(f"{name:<38}{v:>10.1f}")
    unc = results["uncached (avg of 3)"]
    hit = results[f"low-level HIT (avg of {args.hits})"]
    print(f"\nSpeed-up (uncached / low-level hit): {unc / hit:.1f}x")
    print("Cache stats:", requests.get(f"{base}/cache/stats/", params={"date": d}).json())

    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
