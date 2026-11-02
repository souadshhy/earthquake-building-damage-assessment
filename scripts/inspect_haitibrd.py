"""Read-only remote audit of HaitiBRD; saves evidence locally, never trains."""
import argparse
import concurrent.futures
import json
import time
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "technical_checks/test_dataset_search/haitibrd"
BASE = "https://www.designsafe-ci.org"
SYSTEM = "designsafe.storage.published"


def api(kind, path):
    url = f"{BASE}/api/datafiles/tapis/public/{kind}/{SYSTEM}/{urllib.parse.quote(path,safe='')}"
    with urllib.request.urlopen(url+"?limit=100&doi=10.17603%2Fds2-fqat-4v02", timeout=60) as response:
        return json.load(response)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("inventory","preview","download"),default="inventory")
    args=parser.parse_args()
    publication=json.loads((OUT.parent / "haitibrd_publication.json").read_text())
    node=next(n for n in publication["tree"]["children"] if n.get("version")==2)
    objects=node["value"]["fileObjs"]
    if args.stage=="inventory":
        queue=[o["path"] for o in objects if o["type"]=="dir"]
        listing=[o for o in objects if o["type"]!="dir"]
        while queue:
            path=queue.pop(0)
            result=api("listing",path)
            (OUT / f"listing_{len(listing)}.json").write_text(json.dumps(result,indent=2))
            for item in result["listing"]:
                if item["type"]=="dir":
                    queue.append(item["path"])
                else:
                    listing.append(item)
            print(path, len(result["listing"]), flush=True)
        (OUT / "inventory.json").write_text(json.dumps(listing,indent=2))
        print(json.dumps([{k:r.get(k) for k in ("name","path","length")} for r in listing],indent=2))
    elif args.stage=="preview":
        inventory=json.loads((OUT / "inventory.json").read_text())
        # Public preview provides the repository's legitimate download URL.
        selection=[r for r in inventory if r["name"].endswith(".pdf") or r["name"]=="Labeled_image_HaitiBRD.png"]
        selection += [r for r in inventory if r["name"].lower().endswith((".tif",".tiff",".png")) and "original" in r["path"]][:4]
        results=[]
        for row in selection:
            result=api("preview",row["path"])
            results.append({"file":row,"preview":result})
            (OUT / "previews.json").write_text(json.dumps(results,indent=2))
            print(row["name"],json.dumps(result)[:1500],flush=True)
        (OUT / "previews.json").write_text(json.dumps(results,indent=2))
    else:
        inventory=json.loads((OUT / "inventory.json").read_text())
        selected=[r for r in inventory if r["name"].endswith(".pdf") or r["name"]=="Labeled_image_HaitiBRD.png"
                  or "/original/labels/buildings/" in r["path"] or "/original/images/" in r["path"]
                  or "/cropped/labels/buildings/" in r["path"]]
        # Retrieve all 20 paired crops as well to check raster geography and alignment.
        selected += [r for r in inventory if "/cropped/images/" in r["path"]]
        previews=json.loads((OUT / "previews.json").read_text()) if (OUT / "previews.json").exists() else []
        links={r["file"]["path"]:r["preview"]["href"] for r in previews}
        def fetch(row):
            relative=row["path"].split("/data/",1)[1]
            destination=OUT / "files" / relative
            if destination.exists() and destination.stat().st_size==row["length"]:
                return relative
            href=links.get(row["path"])
            if not href:
                href=api("preview",row["path"])["href"]
            destination.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(href, timeout=120) as response:
                data=response.read()
            if len(data)!=row["length"]:
                raise ValueError(f"Unexpected download length {relative}: {len(data)}")
            destination.write_bytes(data)
            return relative
        failures=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(fetch,row):row for row in selected}
            for future in concurrent.futures.as_completed(futures):
                row=futures[future]
                try:
                    print("Verified downloaded size:",future.result(),flush=True)
                except Exception as error:
                    failures.append({"path":row["path"],"error":str(error)})
                    print("Download failed:",row["name"],str(error),flush=True)
        (OUT / "download_failures.json").write_text(json.dumps(failures,indent=2))


if __name__=="__main__":
    main()
