"""Check Git-visible files before pushing; never stages or changes Git history."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={"data","weights","runs","runtime","node_modules",".venv","deliverables","review_ui"}


def main():
    result=subprocess.run(["git","ls-files","--cached","--others","--exclude-standard","-z"],
        cwd=ROOT,check=True,stdout=subprocess.PIPE)
    names=set(result.stdout.decode("utf-8").split("\0"))-{ "" }
    failures=[]
    total=0
    for name in names:
        path=ROOT/name
        if not path.is_file():
            continue
        relative=Path(name)
        size=path.stat().st_size
        total+=size
        if relative.parts[0] in BLOCKED or "node_modules" in relative.parts or relative.name==".env":
            failures.append(f"Local-only file is Git-visible: {name}")
        if size>10*1024*1024:
            failures.append(f"File exceeds 10 MiB source-repository limit: {name}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Repository check passed: {len(names)} Git-visible files, {total/1024/1024:.2f} MiB; no local-only directories or oversized files")
    return 0


if __name__=="__main__":
    sys.exit(main())
