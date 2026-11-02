"""Download the versioned EBD Türkiye archive with resume and full MD5 verification."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    record_path = ROOT / "technical_checks/test_dataset_search/ebd_figshare.json"
    record = json.loads(record_path.read_text())
    artifact = next(f for f in record["files"] if f["name"] == "EARTHQUAKE-TURKEY.zip")
    directory = ROOT / "data/ebd_turkey"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / artifact["name"]
    expected = artifact["computed_md5"]
    def checksum(path):
        digest = hashlib.md5()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8*1024*1024), b""):
                digest.update(block)
        return digest.hexdigest()
    if target.exists() and target.stat().st_size == artifact["size"] and checksum(target) == expected:
        (directory / "source.json").write_text(json.dumps({"article_doi":record["doi"], "artifact":artifact,
            "md5_verified":expected, "license":record["license"],
            "record_metadata_sha256":hashlib.sha256(record_path.read_bytes()).hexdigest()},indent=2))
        print("Archive already present; full MD5 verified", flush=True)
        return
    parts = directory / "download_parts"
    parts.mkdir(exist_ok=True)
    chunk = 16*1024*1024
    ranges = [(i, start, min(start+chunk, artifact["size"])-1)
              for i, start in enumerate(range(0, artifact["size"], chunk))]
    def fetch(item):
        i, start, end = item
        path = parts / f"{i:04d}.part"
        if path.exists() and path.stat().st_size == end-start+1:
            return path
        for attempt in range(4):
            try:
                request = urllib.request.Request(artifact["download_url"], headers={"Range":f"bytes={start}-{end}"})
                with urllib.request.urlopen(request, timeout=180) as response:
                    if response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
                        raise ValueError("Server did not honor the requested range")
                    data = response.read()
                if len(data) != end-start+1:
                    raise ValueError("Incomplete download part")
                path.write_bytes(data)
                return path
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt+1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i, path in enumerate(pool.map(fetch, ranges), 1):
            if i % 4 == 0 or i == len(ranges):
                print(f"Downloaded/verified {i}/{len(ranges)} parts", flush=True)
    with target.open("wb") as stream:
        for i, _, _ in ranges:
            with (parts / f"{i:04d}.part").open("rb") as source:
                for block in iter(lambda: source.read(8*1024*1024), b""):
                    stream.write(block)
    actual = checksum(target)
    if actual != expected:
        raise ValueError(f"Full archive MD5 mismatch: {actual}; expected {expected}")
    (directory / "source.json").write_text(json.dumps({"article_doi":record["doi"], "artifact":artifact,
        "md5_verified":actual, "license":record["license"], "record_metadata_sha256":hashlib.sha256(record_path.read_bytes()).hexdigest()},indent=2))
    print("Complete archive verified:", target, flush=True)


if __name__ == "__main__":
    main()
