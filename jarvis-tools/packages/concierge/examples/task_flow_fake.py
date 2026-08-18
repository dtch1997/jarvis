"""Runnable gen -> train fan-out -> eval join, with no daemon or agent needed."""
import asyncio

from concierge import task_step
from stagehand import Flow, live_dashboard


class FakePool:
    def __init__(self):
        self.records = {}

    def submit(self, spec, **kwargs):
        key = kwargs["dedupe_key"]
        for record in self.records.values():
            if record["dedupe_key"] == key:
                return record["id"]
        tid = f"fake-{len(self.records)}"
        self.records[tid] = {"id": tid, "title": kwargs["title"],
                             "dedupe_key": key, "status": "done",
                             "status_detail": "", "result_text": spec,
                             "output": None}
        return tid

    def get(self, tid):
        return self.records[tid]

    def _returns(self, record, output):
        return record["result_text"]


async def main():
    pool = FakePool()
    flow = Flow("runs/concierge-fake", title="concierge fake DAG", concurrency=3)
    generated = flow.spawn(task_step(
        pool, lambda _: "generate dataset", flow_name="fake-example", poll=0),
        name="generate")
    seeds = flow.expand("seeds", generated, lambda _: [1, 2, 3])
    trained = flow.map("train", seeds, task_step(
        pool, lambda seed: f"train seed={seed}", flow_name="fake-example", poll=0))
    evaluated = flow.reduce("evaluate", trained, task_step(
        pool, lambda results: "evaluate " + ", ".join(r.output for r in results),
        flow_name="fake-example", poll=0))
    async with live_dashboard(flow.runs_dir, title=flow.title):
        await flow.run()
    print(generated.result.output)
    print(evaluated.result.output)
    print(flow.runs_dir / "status.html")


if __name__ == "__main__":
    asyncio.run(main())
