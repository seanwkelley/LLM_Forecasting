"""Regime-shift dynamic SCM (KNOWABLE_WORLDS_DESIGN §15): a lag-1 linear-
Gaussian system whose causal structure CHANGES partway through the recording.

    X_t = c + B_r^T x_{t-1} + eps_t,   eps ~ N(0, sigma^2 I)

where B_r is the lag matrix of the regime active at period t (regime 1 for
t <= t_change, regime 2 after). B has a self-persistence diagonal (every
variable depends on its own previous value) plus sparse cross-lag edges —
the cross-lag edges are "the causal structure" the model is asked about.

Why lag-1: temporal precedence makes the structure FULLY identifiable from
observational data alone (no Markov-equivalence ambiguity), so structure
recovery is a fair ask — an ideal agent could get it from the series we show.

Exact truth: conditional on the observed last row x_{t-1}, next-period values
are Gaussian with mean c + B^T x_{t-1} and sd sigma, so every forecast item
has an analytically exact p* — and an exact STALE answer p_stale (what a
believer in the regime-1 mechanism would say), the perseveration oracle.

Key one-step property: a change to edge i->j alters the next-period
distribution of j ONLY (given the fully observed current state). Every other
node is an automatic within-checkpoint control.

Change types (one change per scenario): edge_add, edge_remove, sign_flip,
weight_double. Candidates that would destabilize the system (spectral radius
>= 0.95) are rejected and redrawn.
"""

from __future__ import annotations

import math

import numpy as np

CHANGE_TYPES = ("edge_add", "edge_remove", "sign_flip", "weight_double",
                "none")   # none = control world: nothing ever changes

Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))  # noqa: E731


class DynSCM:
    def __init__(self, n_nodes: int = 8, edge_prob: float = 0.2, seed: int = 0,
                 noise_scale: float = 1.0, change_type: str = "edge_remove",
                 t_change: int = 60, T: int = 100, n_changes: int = 1):
        assert change_type in CHANGE_TYPES
        assert n_changes >= 1
        self.n = n_nodes
        self.seed = seed
        self.noise_scale = noise_scale
        self.change_type = change_type
        self.n_changes = n_changes
        self.t_change = t_change
        self.T = T
        self.var_names = [f"X{k + 1}" for k in range(n_nodes)]
        rng = np.random.default_rng(seed)

        # regime 1: self-persistence diagonal + sparse cross-lag edges
        # modest self-persistence: keeps the series time-series-like while
        # leaving spectral-radius headroom so cross-lag edges stay STRONG
        # (heavy stabilizer shrinkage would make every edge undetectable)
        B = np.diag(rng.uniform(0.25, 0.5, size=n_nodes))
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j and rng.random() < edge_prob:
                    sign = 1.0 if rng.random() < 0.5 else -1.0
                    B[i, j] = sign * rng.uniform(0.5, 1.0)
        # stabilize: shrink CROSS-lag block only until spectral radius < 0.9
        # (preserves which edges exist; documented deviation from weight_range)
        for _ in range(20):
            rad = max(abs(np.linalg.eigvals(B)))
            if rad < 0.9:
                break
            off = ~np.eye(n_nodes, dtype=bool)
            B[off] *= 0.85
        self.B1 = B
        self.intercept = rng.uniform(-1.0, 1.0, size=n_nodes)

        # regime 2: apply n_changes structural changes, rejecting destabilizers
        self.B2, self.changed_edges = self._apply_change(rng)
        self.changed_edge = self.changed_edges[0]   # back-compat (single-edge)

    # --- regime construction ---
    def _apply_change(self, rng) -> tuple[np.ndarray, list[dict]]:
        if self.change_type == "none":       # control: regime 2 == regime 1;
            off = [(i, j) for i in range(self.n) for j in range(self.n)
                   if i != j and self.B1[i, j] != 0.0]
            i, j = max(off, key=lambda e: abs(self.B1[e[0], e[1]]))
            w = float(self.B1[i, j])         # strongest edge tagged as the
            return self.B1.copy(), [{"i": i, "j": j, "w1": w, "w2": w}]
        off = [(i, j) for i in range(self.n) for j in range(self.n) if i != j]
        present = [(i, j) for i, j in off if self.B1[i, j] != 0.0]
        absent = [(i, j) for i, j in off if self.B1[i, j] == 0.0]
        if self.change_type == "edge_add":
            pool = absent
        else:
            # prefer strong edges: changing a whisper-weight edge is
            # undetectable in principle (regime_gap ~ 0 for every item)
            strong = [(i, j) for i, j in present if abs(self.B1[i, j]) >= 0.35]
            pool = strong if strong else present
        # apply changes sequentially onto B2, each rejecting destabilizers.
        # for n_changes=1 the rng-consumption order is identical to the old
        # single-change code, so all prior single-edge scenarios reproduce.
        order = rng.permutation(len(pool))
        B2 = self.B1.copy()
        changes: list[dict] = []
        for k in order:
            if len(changes) >= self.n_changes:
                break
            i, j = pool[int(k)]
            w1 = float(B2[i, j])
            trial = B2.copy()
            if self.change_type == "edge_add":
                sign = 1.0 if rng.random() < 0.5 else -1.0
                trial[i, j] = sign * rng.uniform(0.6, 1.0)
            elif self.change_type == "edge_remove":
                trial[i, j] = 0.0
            elif self.change_type == "sign_flip":
                trial[i, j] = -w1
            elif self.change_type == "weight_double":
                trial[i, j] = 2.0 * w1
            if max(abs(np.linalg.eigvals(trial))) < 0.95:
                B2 = trial
                changes.append({"i": i, "j": j, "w1": w1,
                                "w2": float(trial[i, j])})
        if len(changes) < self.n_changes:
            raise RuntimeError(f"only {len(changes)}/{self.n_changes} stable "
                               f"{self.change_type} changes (seed {self.seed})")
        return B2, changes

    def B_at(self, t: int) -> np.ndarray:
        """Lag matrix generating period t's values from period t-1."""
        return self.B1 if t <= self.t_change else self.B2

    def cross_edges(self, regime: int) -> list[tuple[int, int]]:
        B = self.B1 if regime == 1 else self.B2
        return [(i, j) for i in range(self.n) for j in range(self.n)
                if i != j and B[i, j] != 0.0]

    def signed_edges(self, regime: int) -> set[str]:
        """Cross-lag edges as 'Xi->Xj:+/-' strings (the elicitation format)."""
        B = self.B1 if regime == 1 else self.B2
        return {f"X{i+1}->X{j+1}:{'+' if B[i, j] > 0 else '-'}"
                for i, j in self.cross_edges(regime)}

    # --- simulation ---
    def simulate(self, seed: int | None = None, burn_in: int = 80) -> np.ndarray:
        """Full series, shape (T, n). Row index t-1 holds period t (1-indexed
        periods). Burn-in under regime 1 is discarded so period 1 starts near
        the stationary distribution."""
        rng = np.random.default_rng(self.seed + 7 if seed is None else seed)
        x = self.intercept + rng.normal(0, self.noise_scale, self.n)
        for _ in range(burn_in):
            x = (self.intercept + self.B1.T @ x
                 + rng.normal(0, self.noise_scale, self.n))
        X = np.zeros((self.T, self.n))
        X[0] = x
        for t in range(2, self.T + 1):
            X[t - 1] = (self.intercept + self.B_at(t).T @ X[t - 2]
                        + rng.normal(0, self.noise_scale, self.n))
        return X

    # --- exact one-step truth ---
    def cond_mean(self, x_prev: np.ndarray, regime: int) -> np.ndarray:
        B = self.B1 if regime == 1 else self.B2
        return self.intercept + B.T @ np.asarray(x_prev, dtype=float)

    def prob_exceed(self, x_prev: np.ndarray, k: int, tau: float,
                    regime: int) -> float:
        mu = float(self.cond_mean(x_prev, regime)[k])
        return 1.0 - Phi((tau - mu) / self.noise_scale)


def fit_var_ols(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS lag-1 fit on a window of the series: returns (B_hat, c_hat) such
    that x_t ~= c_hat + B_hat^T x_{t-1}. The rational-refit baseline."""
    Y, Z = X[1:], X[:-1]
    D = np.column_stack([Z, np.ones(len(Z))])
    coef, *_ = np.linalg.lstsq(D, Y, rcond=None)   # (n+1, n)
    return coef[:-1], coef[-1]


def ols_prob_exceed(B_hat: np.ndarray, c_hat: np.ndarray, x_prev: np.ndarray,
                    k: int, tau: float, sigma: float) -> float:
    mu = float((c_hat + B_hat.T @ np.asarray(x_prev, dtype=float))[k])
    return 1.0 - Phi((tau - mu) / sigma)


if __name__ == "__main__":
    # self-test: exact one-step truth vs Monte Carlo, both regimes
    rng = np.random.default_rng(0)
    worst = 0.0
    for ct in CHANGE_TYPES:
        d = DynSCM(seed=11, change_type=ct)
        X = d.simulate()
        for t_ck, regime in ((40, 1), (70, 2)):
            x_prev = X[t_ck - 1]
            B = d.B_at(t_ck + 1)
            mc = (d.intercept + B.T @ x_prev
                  + rng.normal(0, d.noise_scale, (200_000, d.n)))
            for k in range(d.n):
                tau = float(np.median(mc[:, k]) + 0.6)
                p_mc = float((mc[:, k] > tau).mean())
                p_ex = d.prob_exceed(x_prev, k, tau, regime)
                se = math.sqrt(max(p_mc * (1 - p_mc), 1e-9) / len(mc))
                worst = max(worst, abs(p_ex - p_mc) / max(se, 1e-12))
        ce = d.changed_edge
        print(f"{ct:>14}: edge X{ce['i']+1}->X{ce['j']+1} "
              f"w {ce['w1']:+.2f} -> {ce['w2']:+.2f}  "
              f"radius R1={max(abs(np.linalg.eigvals(d.B1))):.2f} "
              f"R2={max(abs(np.linalg.eigvals(d.B2))):.2f}")
    print(f"worst |exact - MC| = {worst:.2f} SE (should be < ~4)")
