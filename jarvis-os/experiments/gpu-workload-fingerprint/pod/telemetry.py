"""NVML sampler: one JSON line per sample, continuous for the whole session.

Usage: python telemetry.py --hz 10 --out telemetry.jsonl [--gpu 0]
Stops on SIGTERM/SIGINT or when the file named by --stop-file appears.
"""
import argparse, json, os, signal, sys, time

import pynvml as nv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--out", default="telemetry.jsonl")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--stop-file", default="telemetry.stop")
    a = ap.parse_args()

    nv.nvmlInit()
    h = nv.nvmlDeviceGetHandleByIndex(a.gpu)
    name = nv.nvmlDeviceGetName(h)
    name = name.decode() if isinstance(name, bytes) else name
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("flag", True))
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))

    period = 1.0 / a.hz
    n = 0
    with open(a.out, "a", buffering=1) as f:
        f.write(json.dumps({"meta": True, "gpu_name": name, "hz": a.hz, "t0": time.time()}) + "\n")
        next_t = time.time()
        while not stop["flag"] and not os.path.exists(a.stop_file):
            t = time.time()
            rec = {"t": t}
            try:
                u = nv.nvmlDeviceGetUtilizationRates(h)
                m = nv.nvmlDeviceGetMemoryInfo(h)
                rec.update(
                    power_w=nv.nvmlDeviceGetPowerUsage(h) / 1000.0,
                    util_gpu=u.gpu,
                    util_mem=u.memory,
                    mem_used_mb=m.used / 2**20,
                    sm_clock=nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_SM),
                    mem_clock=nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_MEM),
                    temp_c=nv.nvmlDeviceGetTemperature(h, nv.NVML_TEMPERATURE_GPU),
                )
                # each PCIe throughput call samples ~20 ms; fine at 10 Hz
                rec["pcie_tx_kbs"] = nv.nvmlDeviceGetPcieThroughput(h, nv.NVML_PCIE_UTIL_TX_BYTES)
                rec["pcie_rx_kbs"] = nv.nvmlDeviceGetPcieThroughput(h, nv.NVML_PCIE_UTIL_RX_BYTES)
            except nv.NVMLError as e:  # keep sampling; record the error
                rec["err"] = str(e)
            f.write(json.dumps(rec) + "\n")
            n += 1
            next_t += period
            d = next_t - time.time()
            if d > 0:
                time.sleep(d)
            else:  # fell behind (PCIe calls) — resync rather than burst
                next_t = time.time()
    nv.nvmlShutdown()
    print(f"telemetry: {n} samples written to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
