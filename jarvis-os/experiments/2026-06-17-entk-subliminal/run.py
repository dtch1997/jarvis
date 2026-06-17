"""
Phase 0 (ARC-17): reproduce the MNIST subliminal-learning result (paper §6.2).

MLP (784, 256, 256, 10+m), m=3 aux logits, ReLU.
  teacher : train reference init 5 epochs CE on MNIST, 10 REAL logits only.
  student : copy of a reference init, distill the teacher's AUX logits (KL) on
            random NOISE inputs for 5 epochs; real logits never in the loss.
  eval    : accuracy of the student's untrained 10 real logits on MNIST test.

Conditions (per reference seed):
  reference      : untrained reference init                       (B0 floor)
  aux_same       : student=copy(theta0), distill teacher(theta0).aux   <- headline
  all_same       : student=copy(theta0), distill teacher(theta0).all   (B1 ceiling)
  aux_diff       : student=copy(theta0), distill teacher(theta0').aux   (B2 key negative)
  all_diff       : student=copy(theta0), distill teacher(theta0').all   (B3)
theta0' is a DIFFERENT init (different seed); same arch + data. Only the init basis differs.

Headline to reproduce: aux_same > 50% test acc and >> aux_diff (~reference). CPU, minutes.
Decisions (underspecified in paper) are logged to decisions.md.
"""
import argparse, gzip, json, os, struct, urllib.request
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "train_x": "train-images-idx3-ubyte.gz",
    "train_y": "train-labels-idx1-ubyte.gz",
    "test_x": "t10k-images-idx3-ubyte.gz",
    "test_y": "t10k-labels-idx1-ubyte.gz",
}
# Fashion-MNIST is a drop-in: identical IDX format, shape (28x28, 10 classes, 60k/10k), same filenames.
DATASETS = {
    "mnist":   dict(subdir="mnist",   mirror="https://ossci-datasets.s3.amazonaws.com/mnist/",
                    mean=0.1307, std=0.3081),
    "fashion": dict(subdir="fashion", mirror="https://github.com/zalandoresearch/fashion-mnist/raw/master/data/fashion/",
                    mean=0.2860, std=0.3530),
}


# ---------------------------------------------------------------- data
def _download(cfg):
    data = os.path.join(HERE, cfg["subdir"])
    os.makedirs(data, exist_ok=True)
    for fn in FILES.values():
        p = os.path.join(data, fn)
        if not os.path.exists(p):
            urllib.request.urlretrieve(cfg["mirror"] + fn, p)
    return data


def _read_idx(path):
    with gzip.open(path, "rb") as f:
        magic, = struct.unpack(">I", f.read(4))
        ndim = magic & 0xFF
        dims = struct.unpack(">" + "I" * ndim, f.read(4 * ndim))
        return np.frombuffer(f.read(), dtype=np.uint8).reshape(dims)


def load_mnist(dataset=None):
    """Load MNIST or (drop-in) Fashion-MNIST. dataset defaults to $JARVIS_DATASET or 'mnist'."""
    dataset = dataset or os.environ.get("JARVIS_DATASET", "mnist")
    cfg = DATASETS[dataset]
    data = _download(cfg)
    tx = _read_idx(os.path.join(data, FILES["train_x"])).astype(np.float32) / 255.0
    ty = _read_idx(os.path.join(data, FILES["train_y"])).astype(np.int64)
    ex = _read_idx(os.path.join(data, FILES["test_x"])).astype(np.float32) / 255.0
    ey = _read_idx(os.path.join(data, FILES["test_y"])).astype(np.int64)
    tx = (tx.reshape(-1, 784) - cfg["mean"]) / cfg["std"]
    ex = (ex.reshape(-1, 784) - cfg["mean"]) / cfg["std"]
    return (torch.from_numpy(tx), torch.from_numpy(ty),
            torch.from_numpy(ex), torch.from_numpy(ey))


def make_noise(n, kind, seed):
    g = torch.Generator().manual_seed(seed)
    if kind == "gaussian":               # N(0,1) in normalized input space
        return torch.randn(n, 784, generator=g)
    elif kind == "uniform":              # U[0,1] pixels, then MNIST-normalize
        u = torch.rand(n, 784, generator=g)
        return (u - MNIST_MEAN) / MNIST_STD
    raise ValueError(kind)


# ---------------------------------------------------------------- model
class MLP(nn.Module):
    def __init__(self, m=3, width=256, seed=0):
        super().__init__()
        torch.manual_seed(seed)
        self.net = nn.Sequential(
            nn.Linear(784, width), nn.ReLU(),
            nn.Linear(width, width), nn.ReLU(),
            nn.Linear(width, 10 + m),
        )
        self.m = m

    def forward(self, x):
        return self.net(x)              # [N, 10+m]


def clone_init(ref):
    s = MLP(m=ref.m)
    s.load_state_dict(ref.state_dict())
    return s


# ---------------------------------------------------------------- train / distill
def train_teacher(seed, X, y, epochs, batch, lr):
    """Reference init -> 5 epochs CE on the 10 REAL logits only."""
    model = MLP(seed=seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    n = X.shape[0]
    g = torch.Generator().manual_seed(1000 + seed)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            logits = model(X[idx])[:, :10]            # real logits only
            loss = F.cross_entropy(logits, y[idx])
            opt.zero_grad(); loss.backward(); opt.step()
    return model


def distill(student, teacher, noise, epochs, batch, lr, mode):
    """mode='aux' -> KL on the m aux logits only; 'all' -> KL on all 13 logits.
    Inputs are NOISE. Teacher real logits never used when mode='aux'."""
    opt = torch.optim.Adam(student.parameters(), lr=lr)
    n = noise.shape[0]
    teacher.eval()
    with torch.no_grad():
        tlog = teacher(noise)                          # [n, 13]
    g = torch.Generator().manual_seed(7)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            slog = student(noise[idx])
            if mode == "aux":
                tp = F.log_softmax(tlog[idx][:, 10:], dim=1)
                sp = F.log_softmax(slog[:, 10:], dim=1)
            else:
                tp = F.log_softmax(tlog[idx], dim=1)
                sp = F.log_softmax(slog, dim=1)
            loss = F.kl_div(sp, tp, reduction="batchmean", log_target=True)
            opt.zero_grad(); loss.backward(); opt.step()
    return student


@torch.no_grad()
def test_acc(model, Xte, yte):
    pred = model(Xte)[:, :10].argmax(1)
    return (pred == yte).float().mean().item()


# ---------------------------------------------------------------- driver
def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = load_mnist()
    noise = make_noise(args.noise_n, args.noise, seed=123)
    conds = ["reference", "aux_same", "all_same", "aux_diff", "all_diff"]
    out = {c: [] for c in conds}

    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1            # reference init and the "different" init
        ref = MLP(seed=seed0)
        out["reference"].append(test_acc(ref, Xte, yte))

        t_same = train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        t_diff = train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        out.setdefault("_teacher_acc", []).append(test_acc(t_same, Xte, yte))

        for cond, teacher, mode in [
            ("aux_same", t_same, "aux"), ("all_same", t_same, "all"),
            ("aux_diff", t_diff, "aux"), ("all_diff", t_diff, "all"),
        ]:
            st = distill(clone_init(ref), teacher, noise,
                         args.student_epochs, args.batch, args.lr, mode)
            out[cond].append(test_acc(st, Xte, yte))
        print(f"seed {s}: teacher={out['_teacher_acc'][-1]:.3f}  "
              + "  ".join(f"{c}={out[c][-1]:.3f}" for c in conds), flush=True)

    summary = {"config": vars(args)}
    for c in conds + ["_teacher_acc"]:
        a = np.array(out[c])
        summary[c] = {"mean": float(a.mean()), "std": float(a.std()),
                      "sem": float(a.std() / max(1, np.sqrt(len(a)))), "vals": a.tolist()}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    ds = os.environ.get("JARVIS_DATASET", "mnist")
    tag = "" if ds == "mnist" else f"_{ds}"
    with open(os.path.join(HERE, "results", f"phase0{tag}_{args.noise}.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Phase 0 summary (dataset=%s, noise=%s, seeds=%d) ===" % (ds, args.noise, args.seeds))
    for c in ["reference", "aux_diff", "aux_same", "all_diff", "all_same", "_teacher_acc"]:
        m, sem = summary[c]["mean"], summary[c]["sem"]
        print(f"  {c:14s} {m:6.3f} ± {sem:.3f}")
    gate = summary["aux_same"]["mean"] > 0.5 and \
        summary["aux_same"]["mean"] - summary["aux_diff"]["mean"] > 0.15
    print("GATE (aux_same>0.5 and aux_same-aux_diff>0.15):", "PASS" if gate else "FAIL")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=5)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=10000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
