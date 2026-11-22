import json, os, time, multiprocessing.process as mp, pytest
os.makedirs(".cache/coverage", exist_ok=True); OUT = os.path.join(os.path.abspath(".cache/coverage"), "cost-%s.jsonl" % os.environ.get("PYTEST_XDIST_WORKER", "main"))
started = []
_start = mp.BaseProcess.start
def start(self):
    started.append(type(self).__name__)
    return _start(self)
mp.BaseProcess.start = start
@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    started.clear()
    c, w = time.process_time(), time.perf_counter()
    try:
        return (yield)
    finally:
        with open(OUT, "a") as f:
            f.write(json.dumps({"id": item.nodeid, "cpu": time.process_time() - c, "wall": time.perf_counter() - w, "procs": len(started), "w": os.environ.get("PYTEST_XDIST_WORKER")}) + "\n")
