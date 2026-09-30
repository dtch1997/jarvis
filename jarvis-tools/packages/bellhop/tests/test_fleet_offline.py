"""Offline tests for bellhop.fleet: no Docker daemon, no Modal account.

The Docker backend is driven through a stand-in for its ``_run`` helper; the
Modal backend through a fake ``modal`` module. Both check the contract in
docs/design/sandbox-fleet.md: argv/kwargs, result mapping, error mapping,
capacity and cleanup.
"""

import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest

from bellhop.errors import PreflightError, SandboxError
from bellhop.fleet import (
    RUN_KEY,
    TIMEOUT_RC,
    DockerFleet,
    Limits,
    ModalFleet,
    make_fleet,
    parse_docker_size,
)
from bellhop.fleet import base as fleet_base
from bellhop.fleet import docker as fleet_docker
from bellhop.fleet import modal as fleet_modal
from bellhop.fleet.base import BaseSandbox, Fleet, gather_timed, safe_name, wrap_command


# --- the contract ------------------------------------------------------------------------

def test_wrap_command_matches_mimoagent_convention():
    argv = wrap_command("pytest -x", "/work dir", 60)
    assert argv[:4] == ["timeout", "60", "/bin/bash", "-lc"]
    assert argv[4] == "exec 2>&1 </dev/null\ncd '/work dir' && pytest -x"


def test_wrap_command_never_disables_the_timeout():
    # `timeout 0` means "no timeout" to coreutils; fractions round up.
    assert wrap_command("x", "/", 0.2)[1] == "1"
    assert wrap_command("x", "/", 2.5)[1] == "3"


def test_safe_name_and_limits_validation():
    assert safe_name("task/000123 v2") == "task-000123-v2"
    assert safe_name("///") == "x"
    with pytest.raises(PreflightError):
        Limits(cpu=0)


def test_make_fleet_by_name():
    assert isinstance(make_fleet("docker", "r"), DockerFleet)
    assert isinstance(make_fleet("modal", "r"), ModalFleet)
    with pytest.raises(PreflightError):
        make_fleet("k8s")


class _FakeSandbox(BaseSandbox):
    async def _teardown(self):
        self.torn_down = True


class _FakeFleet(Fleet):
    backend = "fake"

    def __init__(self, *a, fail=False, **kw):
        super().__init__(*a, **kw)
        self.fail = fail
        self.gc_calls = 0
        self.created = []

    async def _create(self, image, *, env, limits, name_hint):
        if self.fail:
            raise SandboxError("boom")
        sb = _FakeSandbox(f"{image}-{len(self.created)}", image)
        self.created.append((image, env, limits, name_hint))
        return sb

    async def gc(self):
        self.gc_calls += 1
        return 0


def test_max_live_blocks_open_until_a_sandbox_closes():
    async def go():
        fleet = _FakeFleet("r", max_live=1)
        a = await fleet.open("img")
        waiter = asyncio.create_task(fleet.open("img"))
        await asyncio.sleep(0.05)
        assert not waiter.done()                     # the slot is taken
        await a.close()
        b = await asyncio.wait_for(waiter, 1)
        assert [s.id for s in fleet.live] == [b.id]
        await a.close()                              # idempotent: frees nothing twice
        assert fleet._slots.used == 1
    asyncio.run(go())


def test_failed_open_returns_its_slot():
    async def go():
        fleet = _FakeFleet("r", max_live=1, fail=True)
        for _ in range(2):
            with pytest.raises(SandboxError):
                await fleet.open("img")
        assert fleet._slots.used == 0
    asyncio.run(go())


def test_group_bigger_than_capacity_is_rejected():
    async def go():
        with pytest.raises(PreflightError):
            await fleet_base._Slots(2).acquire(3)
    asyncio.run(go())


def test_context_exit_closes_live_sandboxes_and_sweeps_the_run():
    async def go():
        async with _FakeFleet("r", limits=Limits(cpu=1, memory_mb=256)) as fleet:
            a = await fleet.open("img", env={"K": "v"}, name_hint="task/1")
            assert fleet.created == [("img", {"K": "v"}, Limits(cpu=1, memory_mb=256), "task-1")]
        assert a.closed and a.torn_down and a.ended_at is not None
        assert fleet.live == [] and fleet.gc_calls == 1
    asyncio.run(go())


def test_gather_timed_reports_every_failure():
    async def one(ref):
        if ref.startswith("bad"):
            raise RuntimeError(f"no {ref}")

    async def go():
        assert set(await gather_timed(["a", "a", "b"], one, 2)) == {"a", "b"}
        with pytest.raises(SandboxError) as e:
            await gather_timed(["a", "bad1", "bad2"], one, 2)
        assert "bad1" in str(e.value) and "bad2" in str(e.value)
    asyncio.run(go())


# --- Docker ------------------------------------------------------------------------------

class _DockerCLI:
    """Stands in for fleet.docker._run: records argv, answers from a rule list."""

    def __init__(self, rules=()):
        self.calls = []
        self.rules = list(rules)

    async def __call__(self, argv, *, stdin=None, timeout, max_output_bytes=None):
        self.calls.append(list(argv))
        for match, answer in self.rules:
            if match(argv):
                return answer
        return 0, b"", False, False


def _docker(monkeypatch, rules=()):
    cli = _DockerCLI(rules)
    monkeypatch.setattr(fleet_docker, "_run", cli)
    monkeypatch.setattr(fleet_docker.shutil, "which", lambda _: "/usr/bin/docker")
    return cli


def test_docker_create_argv(monkeypatch):
    cli = _docker(monkeypatch)

    async def go():
        fleet = DockerFleet("run-1", limits=Limits(cpu=2, memory_mb=4096, pids=512), min_free_gb=None)
        sb = await fleet.open("repo:tag", env={"A": "1"}, name_hint="t9")
        return sb

    sb = asyncio.run(go())
    run = cli.calls[0]
    assert run[:3] == ["docker", "run", "-d"]
    assert run[run.index("--label") + 1] == f"{RUN_KEY}=run-1"
    assert run[run.index("--network") + 1] == "none"
    assert run[run.index("--cpus") + 1] == "2"
    assert run[run.index("--memory") + 1] == "4096m" == run[run.index("--memory-swap") + 1]
    assert run[run.index("--pids-limit") + 1] == "512"
    assert "--init" in run and ["-e", "A=1"] == run[run.index("-e"):run.index("-e") + 2]
    assert run[-5:] == ["--entrypoint", "/bin/sh", "repo:tag", "-c", "tail -f /dev/null"]
    assert sb.id.startswith("bellhop-run-1-t9-") and sb.ip is None


def test_docker_create_failure_is_a_sandbox_error(monkeypatch):
    _docker(monkeypatch, [(lambda a: a[:2] == ["docker", "run"], (125, b"pull access denied", False, False))])

    async def go():
        fleet = DockerFleet("r", min_free_gb=None)
        with pytest.raises(SandboxError, match="pull access denied"):
            await fleet.open("nope:1")
        assert fleet._slots.used == 0
    asyncio.run(go())


def test_docker_named_network_records_the_ip(monkeypatch):
    _docker(monkeypatch, [(lambda a: a[:2] == ["docker", "inspect"], (0, b"10.0.0.7\n", False, False))])

    async def go():
        return await DockerFleet("r", network="agentrl-net", min_free_gb=None).open("img")
    assert asyncio.run(go()).ip == "10.0.0.7"


def _exec_rule(answer):
    return (lambda a: a[:2] == ["docker", "exec"] and "-i" not in a, answer)


@pytest.mark.parametrize("answer, expected", [
    ((0, b"ok\n", False, False), (0, "ok\n", False, False)),
    ((124, b"", False, False), (TIMEOUT_RC, "", True, False)),       # in-sandbox timeout
    ((-1, b"part", True, False), (TIMEOUT_RC, "part", True, False)),  # client backstop
    ((0, b"xx", False, True), (0, "xx", False, True)),               # output cap
])
def test_docker_exec_result_mapping(monkeypatch, answer, expected):
    cli = _docker(monkeypatch, [_exec_rule(answer)])

    async def go():
        sb = await DockerFleet("r", min_free_gb=None).open("img")
        return await sb.exec("do it", workdir="/w", timeout=5, max_output_bytes=2), sb

    res, sb = asyncio.run(go())
    assert (res.exit_code, res.output, res.timed_out, res.truncated) == expected
    exec_argv = [c for c in cli.calls if c[:2] == ["docker", "exec"]][0]
    assert exec_argv[2] == sb.id and exec_argv[3:6] == ["timeout", "5", "/bin/bash"]


def test_docker_exec_container_gone_is_infra_only_when_inspect_agrees(monkeypatch):
    gone = (1, b"Error response from daemon: No such container: x", False, False)

    async def go(alive: bool):
        _docker(monkeypatch, [
            _exec_rule(gone),
            (lambda a: a[:2] == ["docker", "inspect"], (0, b"true" if alive else b"false", False, False)),
        ])
        sb = await DockerFleet("r", min_free_gb=None).open("img")
        return await sb.exec("echo 'No such container'")

    with pytest.raises(SandboxError):
        asyncio.run(go(alive=False))
    assert asyncio.run(go(alive=True)).exit_code == 1    # the workload printed the text


def test_docker_file_errors(monkeypatch):
    _docker(monkeypatch, [
        (lambda a: a[:3] == ["docker", "exec", "-i"], (1, b"read-only file system", False, False)),
        _exec_rule((1, b"cat: /x: No such file", False, False)),
    ])

    async def go():
        sb = await DockerFleet("r", min_free_gb=None).open("img")
        with pytest.raises(SandboxError, match="read-only"):
            await sb.write_file("/x", "data")
        with pytest.raises(FileNotFoundError):
            await sb.read_file("/x")
    asyncio.run(go())


def test_docker_host_floor_gives_up(monkeypatch):
    cli = _docker(monkeypatch)

    async def go():
        fleet = DockerFleet("r", min_free_gb=20, free_wait_s=0)

        async def low():
            return int(5e9)
        fleet.free_bytes = low
        with pytest.raises(SandboxError, match="under the 20 GB floor"):
            await fleet.open("img")
        assert fleet._slots.used == 0
    asyncio.run(go())
    assert not any(c[:2] == ["docker", "run"] for c in cli.calls)


def test_docker_disk_guard_kills_only_capped_sandboxes_over_their_cap(monkeypatch):
    cli = _docker(monkeypatch)

    async def go():
        fleet = DockerFleet("r", limits=Limits(disk_gb=1), min_free_gb=None, guard_interval_s=3600)
        big = await fleet.open("img")
        small = await fleet.open("img")
        uncapped = await fleet.open("img", limits=Limits(disk_gb=None))
        ps = "\n".join([f"{big.id}\t2.5GB (virtual 3GB)", f"{small.id}\t20MB (virtual 3GB)",
                        f"{uncapped.id}\t9GB (virtual 12GB)"]).encode()
        cli.rules.insert(0, (lambda a: a[:3] == ["docker", "ps", "--size"], (0, ps, False, False)))
        assert await fleet.check_disk() == [big.id]
        assert await fleet.check_disk() == []            # killed once only
        assert fleet.disk_killed == {big.id}
        await fleet.aclose()
        return big.id

    big_id = asyncio.run(go())
    assert [c for c in cli.calls if c[:2] == ["docker", "kill"]] == [["docker", "kill", big_id]]


def test_parse_docker_size():
    assert parse_docker_size("1.6MB (virtual 1.08GB)") == pytest.approx(1.6e6)
    assert parse_docker_size("0B") == 0
    assert parse_docker_size("") == 0


def test_gc_docker_filters_by_label_and_age(monkeypatch):
    inspect_out = (b"aaa 2020-01-01T00:00:00.123456789Z\n"
                   b"bbb 2999-01-01T00:00:00Z\n")
    cli = _docker(monkeypatch, [
        (lambda a: a[:3] == ["docker", "ps", "-aq"], (0, b"aaa\nbbb\n", False, False)),
        (lambda a: a[:2] == ["docker", "inspect"], (0, inspect_out, False, False)),
    ])
    assert asyncio.run(fleet_docker.gc_docker("run-9")) == 2
    assert ["docker", "ps", "-aq", "--filter", f"label={RUN_KEY}=run-9"] in cli.calls
    assert ["docker", "rm", "-f", "aaa", "bbb"] in cli.calls

    cli.calls.clear()
    assert asyncio.run(fleet_docker.gc_docker(older_than=timedelta(hours=1))) == 1
    assert ["docker", "ps", "-aq", "--filter", f"label={RUN_KEY}"] in cli.calls
    assert ["docker", "rm", "-f", "aaa"] in cli.calls


def test_docker_prefetch_pulls_only_missing_images(monkeypatch):
    cli = _docker(monkeypatch, [
        (lambda a: a[:3] == ["docker", "image", "inspect"] and a[3] == "have:1", (0, b"[]", False, False)),
        (lambda a: a[:3] == ["docker", "image", "inspect"], (1, b"No such image", False, False)),
    ])
    timings = asyncio.run(DockerFleet("r").prefetch(["have:1", "need:1", "need:1"]))
    assert set(timings) == {"have:1", "need:1"}
    assert [c for c in cli.calls if c[:2] == ["docker", "pull"]] == [["docker", "pull", "need:1"]]


# --- Modal -------------------------------------------------------------------------------

class _Aio:
    def __init__(self, fn):
        self.aio = fn


class _Stream:
    def __init__(self, chunks=()):
        self.chunks = list(chunks)

        async def read():
            return b"".join(self.chunks)
        self.read = _Aio(read)

    def __aiter__(self):
        async def gen():
            for c in self.chunks:
                yield c
        return gen()


class _Stdin:
    def __init__(self):
        self.data = b""
        self.eof = False

        async def drain():
            return None
        self.drain = _Aio(drain)

    def write(self, b):
        self.data += b

    def write_eof(self):
        self.eof = True


class _Proc:
    def __init__(self, rc=0, out=(), err=()):
        self.stdout, self.stderr, self.stdin = _Stream(out), _Stream(err), _Stdin()

        async def wait():
            return rc
        self.wait = _Aio(wait)


class _ModalSandbox:
    def __init__(self, object_id="sb-1", procs=(), alive=True, exec_error=None):
        self.object_id = object_id
        self.procs = list(procs)
        self.execs = []
        self.alive = alive
        self.terminated = False

        async def exec_(*argv, **kw):
            self.execs.append((argv, kw))
            if exec_error is not None:
                raise exec_error
            return self.procs.pop(0) if self.procs else _Proc()

        async def poll():
            return None if self.alive else 137

        async def terminate(**kw):
            self.terminated = True
        self.exec, self.poll, self.terminate = _Aio(exec_), _Aio(poll), _Aio(terminate)


def _fake_modal(sandbox=None, listed=()):
    created, built, looked_up = [], [], []

    class Image:
        def __init__(self, ref, kw):
            self.ref, self.kw = ref, kw

            async def build(app):
                built.append(ref)
            self.build = _Aio(build)

        @staticmethod
        def from_registry(ref, **kw):
            return Image(ref, kw)

    async def create(*args, **kw):
        created.append({"args": args, **kw})
        return sandbox or _ModalSandbox()

    async def lookup(name, create_if_missing=False):
        looked_up.append(name)
        return SimpleNamespace(app_id=f"ap-{name}")

    def list_(app_id=None, tags=None):
        async def gen():
            for sb in listed:
                if tags is None or all(sb.tags.get(k) == v for k, v in tags.items()):
                    yield sb
        return gen()

    mod = SimpleNamespace(
        Image=Image,
        Sandbox=SimpleNamespace(create=_Aio(create), list=_Aio(list_)),
        App=SimpleNamespace(lookup=_Aio(lookup)),
    )
    return mod, created, built, looked_up


def _use_modal(monkeypatch, **kw):
    mod, created, built, looked_up = _fake_modal(**kw)
    monkeypatch.setattr(fleet_modal, "_import_modal", lambda: mod)
    return created, built, looked_up


def test_modal_create_kwargs_mirror_docker_hard_limits():
    fleet = ModalFleet("run-1", limits=Limits(cpu=1.5, memory_mb=2048), max_lifetime=timedelta(hours=3))
    kw = fleet.create_kwargs(image="IMG", app="APP", env={"K": "v"}, limits=fleet.limits, name_hint="t1")
    assert kw["cpu"] == (1.5, 1.5) and kw["memory"] == (2048, 2048)
    assert kw["timeout"] == 3 * 3600
    assert kw["tags"] == {RUN_KEY: "run-1", fleet_modal.NAME_KEY: "t1"}
    assert kw["block_network"] is True and kw["env"] == {"K": "v"}
    assert "outbound_domain_allowlist" not in kw and "region" not in kw


def test_modal_network_policy():
    kw = ModalFleet("r", outbound_domain_allowlist=["proxy.example.com"]).create_kwargs(
        image=None, app=None, env={}, limits=Limits())
    assert kw["block_network"] is False and kw["outbound_domain_allowlist"] == ["proxy.example.com"]
    assert "env" not in kw
    assert ModalFleet("r", block_network=False).block_network is False
    with pytest.raises(PreflightError):
        ModalFleet("r", block_network=True, outbound_cidr_allowlist=["10.0.0.0/8"])


@pytest.mark.parametrize("hours", [0, 25])
def test_modal_lifetime_bounds(hours):
    with pytest.raises(PreflightError):
        ModalFleet("r", max_lifetime=timedelta(hours=hours))


def test_modal_open_builds_one_image_per_ref_and_tags_the_run(monkeypatch):
    created, _, looked_up = _use_modal(monkeypatch)

    async def go():
        fleet = ModalFleet("run-7", app_name="fleet-app", add_python="3.12")
        a = await fleet.open("repo:1", name_hint="a")
        b = await fleet.open("repo:1", name_hint="b")
        return fleet, a, b

    fleet, a, b = asyncio.run(go())
    assert looked_up == ["fleet-app"]                           # app looked up once
    assert created[0]["image"] is created[1]["image"]           # image object cached per ref
    assert created[0]["image"].kw == {"add_python": "3.12"}
    assert created[0]["tags"][RUN_KEY] == "run-7" and created[1]["tags"][fleet_modal.NAME_KEY] == "b"
    # the sandbox idles on its own process: flattened task images have no CMD, and Modal exits them at once
    assert created[0]["args"] == fleet_modal.IDLE_COMMAND == ("/bin/sh", "-c", "tail -f /dev/null")
    assert a.id == "sb-1" and a.image == "repo:1"


def test_modal_create_failure_is_a_sandbox_error(monkeypatch):
    mod, *_ = _fake_modal()

    async def boom(*args, **kw):
        raise RuntimeError("ImageBuildError: no python")
    mod.Sandbox.create = _Aio(boom)
    monkeypatch.setattr(fleet_modal, "_import_modal", lambda: mod)

    async def go():
        fleet = ModalFleet("r", max_live=1)
        with pytest.raises(SandboxError, match="no python"):
            await fleet.open("img")
        assert fleet._slots.used == 0
    asyncio.run(go())


def _modal_exec(monkeypatch, sandbox, **exec_kw):
    _use_modal(monkeypatch, sandbox=sandbox)

    async def go():
        sb = await ModalFleet("r").open("img")
        return await sb.exec("run it", workdir="/w", timeout=exec_kw.pop("timeout", 10), **exec_kw)
    return asyncio.run(go())


def test_modal_exec_argv_and_output(monkeypatch):
    fake = _ModalSandbox(procs=[_Proc(0, out=[b"hel", b"lo\n"])])
    res = _modal_exec(monkeypatch, fake)
    assert (res.exit_code, res.output, res.timed_out, res.truncated) == (0, "hello\n", False, False)
    argv, kw = fake.execs[0]
    assert list(argv) == wrap_command("run it", "/w", 10)
    assert kw == {"timeout": 10 + fleet_base.CLIENT_GRACE_S, "text": False}


def test_modal_exec_caps_output_across_chunks_and_streams(monkeypatch):
    fake = _ModalSandbox(procs=[_Proc(0, out=[b"abcd", b"efgh"], err=[b"ERR"])])
    res = _modal_exec(monkeypatch, fake, max_output_bytes=6)
    assert res.output == "abcdef" and res.truncated


@pytest.mark.parametrize("rc, timed_out", [(124, True), (fleet_modal.MODAL_EXEC_TIMEOUT_RC, True), (1, False)])
def test_modal_exec_timeouts(monkeypatch, rc, timed_out):
    res = _modal_exec(monkeypatch, _ModalSandbox(procs=[_Proc(rc)]))
    assert res.timed_out is timed_out
    assert res.exit_code == (TIMEOUT_RC if timed_out else rc)


def test_modal_exec_on_a_dead_sandbox_is_infra(monkeypatch):
    with pytest.raises(SandboxError, match="terminated"):
        _modal_exec(monkeypatch, _ModalSandbox(procs=[_Proc(137)], alive=False))
    with pytest.raises(SandboxError, match="SandboxTerminatedError"):
        _modal_exec(monkeypatch, _ModalSandbox(exec_error=type("SandboxTerminatedError", (Exception,), {})("x")))


def test_modal_exec_timeout_exception_reads_as_a_timeout(monkeypatch):
    res = _modal_exec(monkeypatch, _ModalSandbox(exec_error=type("ExecTimeoutError", (Exception,), {})("x")))
    assert res.timed_out and res.exit_code == TIMEOUT_RC


def test_modal_files(monkeypatch):
    write_proc, read_proc, missing = _Proc(0), _Proc(0, out=[b"content"]), _Proc(1, err=[b"cat: nope"])
    fake = _ModalSandbox(procs=[write_proc, read_proc, missing])
    _use_modal(monkeypatch, sandbox=fake)

    async def go():
        sb = await ModalFleet("r").open("img")
        await sb.write_file("/a b/c.sh", "echo hi", executable=True)
        assert await sb.read_file("/a b/c.sh", max_bytes=100) == "content"
        with pytest.raises(FileNotFoundError, match="cat: nope"):
            await sb.read_file("/nope")
    asyncio.run(go())
    assert write_proc.stdin.data == b"echo hi" and write_proc.stdin.eof
    assert fake.execs[0][0][:2] == ("/bin/sh", "-c") and "chmod +x '/a b/c.sh'" in fake.execs[0][0][2]
    assert fake.execs[1][0][2] == "head -c 100 '/a b/c.sh'"


def test_modal_close_terminates_once(monkeypatch):
    fake = _ModalSandbox()
    _use_modal(monkeypatch, sandbox=fake)

    async def go():
        async with ModalFleet("r") as fleet:
            sb = await fleet.open("img")
            await sb.close()
            await sb.close()
            assert fleet.live == []
    asyncio.run(go())
    assert fake.terminated


def test_gc_modal_terminates_only_the_runs_sandboxes(monkeypatch):
    mine = _ModalSandbox("sb-mine")
    mine.tags = {RUN_KEY: "run-1"}
    other = _ModalSandbox("sb-other")
    other.tags = {RUN_KEY: "run-2"}
    _use_modal(monkeypatch, listed=[mine, other])
    assert asyncio.run(fleet_modal.gc_modal("run-1")) == 1
    assert mine.terminated and not other.terminated
    assert asyncio.run(fleet_modal.gc_modal()) == 2


def test_modal_prefetch_builds_each_image_once(monkeypatch):
    _, built, _ = _use_modal(monkeypatch)
    timings = asyncio.run(ModalFleet("r").prefetch(["a:1", "b:1", "a:1"]))
    assert sorted(built) == ["a:1", "b:1"] and set(timings) == {"a:1", "b:1"}


# --- CLI ---------------------------------------------------------------------------------

def test_cli_fleet_gc(monkeypatch, capsys):
    from bellhop import cli
    from bellhop import fleet as fleet_pkg

    seen = []

    async def fake_gc_docker(run_id=None, *, older_than=None):
        seen.append((run_id, older_than))
        return 3
    monkeypatch.setattr(fleet_pkg, "gc_docker", fake_gc_docker)

    assert cli.main(["fleet", "gc", "--backend", "docker", "--run", "r1"]) == 0
    assert cli.main(["fleet", "gc", "--backend", "docker", "--older-than-hours", "2"]) == 0
    assert seen == [("r1", None), (None, timedelta(hours=2))]
    assert "removed 3 docker sandbox(es) (run r1)" in capsys.readouterr().out
    # a bare modal gc would hit live runs, so it demands --run or --all
    assert cli.main(["fleet", "gc", "--backend", "modal"]) == 2
