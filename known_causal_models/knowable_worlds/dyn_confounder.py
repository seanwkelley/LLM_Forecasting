"""Hidden-confounder dynamic world (KNOWABLE_WORLDS_DESIGN §16.3): the causal
core of the dynamic arm.

The observational-VAR arm (dyn_engine.py) is deliberately confound-free: with
lag-1 temporal precedence the structure is identifiable from observation
alone, so an idealized statistician (rolling OLS) is the ceiling and causality
adds nothing beyond it. That makes it a strong *belief-updating* test but a
weak *causal* one. This module removes that ceiling.

Structure (one latent confounder U, never shown to the model):

        U ─► A          U ─► B          C ─► B
        (confound)      (confound)      (true cause)

    - A and B are both driven by the hidden U, so they co-move: OBSERVING A
      is evidence about B. But A does NOT cause B.
    - C genuinely causes B.
    - In INTERVENTION periods, A is set exogenously (do(A)); this severs U→A,
      so A carries no information about U — hence none about B.

The lag-1 VAR provides time-series texture (each period depends on the last);
the confound and the causal edge are injected CONTEMPORANEOUSLY within a
period, in topological order (U, then C, then A and B), so every forecast has
a closed-form exact answer (i.i.d. U ⇒ no latent-state filtering needed).

Why this is causal, not statistical: the see-vs-do forecast pair on the same
value a diverges only if the model has the causal structure right —
    see(A=a):  uses a   (a is evidence about U, hence about B)
    do(A=a):   ignores a (the intervention severs U→A)
A model without causal structure answers both identically and fails one; a
pooled-OLS statistician fits a biased A→B slope and mis-forecasts the do rows,
so the statistician ceiling drops BELOW the truth. do(C) (C a real cause,
intervened value must be USED) blocks the "ignore all interventions" heuristic.
"""

from __future__ import annotations

import math

import numpy as np

Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))  # noqa: E731

# forecast query types: observational baseline, see/do on the confounded
# non-cause A, and see/do on the true cause C
QUERY_TYPES = ("obs", "see_A", "do_A", "see_C", "do_C")


class ConfoundedDynSCM:
    """Lag-1 VAR with a hidden contemporaneous confounder + a true cause.

    Indices are fixed: A=0 (confounded non-cause of B), B=1 (target),
    C=2 (true cause of B); variables 3..n-1 are unconfounded filler with
    ordinary lag dynamics.
    """

    A, B, C = 0, 1, 2

    def __init__(self, n_nodes: int = 8, edge_prob: float = 0.2, seed: int = 0,
                 noise_scale: float = 1.0, sigma_u: float = 1.2,
                 lam_a: float = 1.1, lam_b: float = 1.1, gamma: float = 0.9,
                 intervene_frac: float = 0.25, t_change: int = 60, T: int = 100,
                 intervene_from: int | None = None):
        assert n_nodes >= 4
        self.n = n_nodes
        self.seed = seed
        self.noise_scale = noise_scale
        self.sigma_u = sigma_u
        self.lam_a = lam_a          # U -> A loading
        self.lam_b = lam_b          # U -> B loading
        self.gamma = gamma          # C -> B causal coefficient (contemporaneous)
        self.intervene_frac = intervene_frac
        self.t_change = t_change
        self.T = T
        # interventions on A begin at `intervene_from` (default: throughout, so
        # the model can LEARN the confound signature; set to t_change for the
        # policy-rule-change / Lucas framing where assignment starts at t*)
        self.intervene_from = 1 if intervene_from is None else intervene_from
        self.var_names = [f"X{k + 1}" for k in range(n_nodes)]

        rng = np.random.default_rng(seed)
        # lag-1 VAR among observed variables: self-persistence + sparse cross
        B1 = np.diag(rng.uniform(0.25, 0.5, size=n_nodes))
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j and rng.random() < edge_prob:
                    sign = 1.0 if rng.random() < 0.5 else -1.0
                    B1[i, j] = sign * rng.uniform(0.5, 1.0)
        # keep B (the target) clean: its ONLY parents are its own lag, the
        # contemporaneous cause C (via gamma) and the contemporaneous U (via
        # lam_b). No lagged edge into B — so A is a pure non-cause of B.
        B1[:, self.B] = 0.0
        B1[self.B, self.B] = rng.uniform(0.25, 0.45)
        # A must not be a lagged cause of B either (already zeroed); leave A's
        # own parents so it has time-series texture.
        # Stabilize the EFFECTIVE transition matrix, not B1 alone: the
        # contemporaneous injection x[B] += gamma * x[C] makes the dynamics
        # x_t = M^T x_{t-1} + ... with M = B1 except column B, which is
        # B1[:, B] + gamma * B1[:, C]. Checking only B1 admits explosive
        # worlds (audit 2026-07-07: 10/60 seeds diverged, incl. seed 300).
        def effective(Bm):
            M = Bm.copy()
            M[:, self.B] = Bm[:, self.B] + self.gamma * Bm[:, self.C]
            return M
        for _ in range(40):                       # stabilize cross-lag block
            if max(abs(np.linalg.eigvals(effective(B1)))) < 0.9:
                break
            off = ~np.eye(n_nodes, dtype=bool)
            B1[off] *= 0.85
        else:
            raise RuntimeError(f"seed {seed}: could not stabilize the "
                               "effective transition matrix")
        self.B1 = B1
        self.intercept = rng.uniform(-0.5, 0.5, size=n_nodes)
        self._rng_seed_for_sim = seed + 7
        # Random intervention schedule (~intervene_frac of eligible periods),
        # fixed by the world's seed. A deterministic every-4th schedule let a
        # sharp model PREDICT that the next period is an intervention period,
        # contradicting the see-question's "arises naturally" stipulation
        # (audit 2026-07-07); randomizing removes that, and makes
        # intervene_frac a live parameter. Redraw until the first 30 periods
        # carry at least 5 labeled interventions (learnability floor).
        sched_rng = np.random.default_rng(seed + 13)
        for _ in range(200):
            mask = sched_rng.random(self.T + 1) < self.intervene_frac
            mask[:self.intervene_from] = False
            if self.intervene_from <= 25 and mask[1:31].sum() < 5:
                continue
            break
        self._interv_mask = mask                  # index by period t (1-based)

    # --- per-period base means (given the previous observed row) ---
    def base_mean(self, x_prev: np.ndarray) -> np.ndarray:
        """E[x_t | x_{t-1}] from the lag VAR alone (before U/C injection)."""
        return self.intercept + self.B1.T @ np.asarray(x_prev, dtype=float)

    def is_intervened(self, t: int) -> bool:
        """Seeded random intervention schedule (~intervene_frac of periods)."""
        return t >= self.intervene_from and bool(self._interv_mask[t])

    # --- simulation ---
    def simulate(self, burn_in: int = 60) -> np.ndarray:
        """Observed series, shape (T, n). U and the intervention values are
        stored (U hidden from the model, revealed only to the oracle)."""
        rng = np.random.default_rng(self._rng_seed_for_sim)
        X = np.zeros((self.T, self.n))
        self.U = np.zeros(self.T)
        self.interv_val = np.full(self.T, np.nan)   # A's set value where done
        x_prev = rng.normal(0, 1, self.n)
        # burn-in under the same (observational) dynamics
        for _ in range(burn_in):
            u = rng.normal(0, self.sigma_u)
            x = self.base_mean(x_prev) + rng.normal(0, self.noise_scale, self.n)
            x[self.C] = x[self.C]                     # C unconfounded
            x[self.B] += self.gamma * x[self.C] + self.lam_b * u
            x[self.A] += self.lam_a * u
            x_prev = x
        for t in range(1, self.T + 1):
            u = rng.normal(0, self.sigma_u)
            x = self.base_mean(x_prev) + rng.normal(0, self.noise_scale, self.n)
            # contemporaneous injections in topological order: C, then U->A/B,
            # then C->B
            x[self.B] += self.gamma * x[self.C] + self.lam_b * u
            if self.is_intervened(t):
                # do(A): overwrite A independently of U (severs U->A). B is
                # UNAFFECTED because A does not cause B.
                a_val = float(rng.normal(0, 2.5))
                x[self.A] = a_val
                self.interv_val[t - 1] = a_val
            else:
                x[self.A] += self.lam_a * u
            self.U[t - 1] = u
            X[t - 1] = x
            x_prev = x
        return X

    # --- exact forecast oracles for period ck+1, given the row x_ck ---
    def _forecast_moments(self, x_ck: np.ndarray):
        """Baseline mean/var of B_{ck+1} and the confound regression slope."""
        mu = self.base_mean(x_ck)                    # E[x_{ck+1} | x_ck]
        mu_C = float(mu[self.C])
        # E[B] baseline = lag term + gamma * E[C]  (U averages to 0)
        mean_B = float(mu[self.B]) + self.gamma * mu_C
        var_C = self.noise_scale ** 2                # C = base + noise
        # A_{ck+1} = mu_A + lam_a U + noise ; B gets lam_b U
        mu_A = float(mu[self.A])
        var_A = self.lam_a ** 2 * self.sigma_u ** 2 + self.noise_scale ** 2
        cov_AB = self.lam_a * self.lam_b * self.sigma_u ** 2
        var_B = (self.lam_b ** 2 * self.sigma_u ** 2 + self.noise_scale ** 2
                 + self.gamma ** 2 * var_C)          # marginal over C and U
        beta_conf = cov_AB / var_A                   # see(A) regression slope
        return mean_B, var_B, mu_A, mu_C, beta_conf

    def p_star(self, x_ck: np.ndarray, query: str, tau: float,
               value: float = 0.0) -> float:
        """Exact P(B_{ck+1} > tau) under the CORRECT causal reading."""
        mean_B, var_B, mu_A, mu_C, beta = self._forecast_moments(x_ck)
        if query == "obs":
            m, v = mean_B, var_B
        elif query == "see_A":       # observing A=value: use it (evidence on U)
            var_A = self.lam_a ** 2 * self.sigma_u ** 2 + self.noise_scale ** 2
            m = mean_B + beta * (value - mu_A)
            v = var_B - beta ** 2 * var_A            # residual var after cond.
        elif query == "do_A":        # setting A=value: ignore it (severs U->A)
            m, v = mean_B, var_B
        elif query in ("see_C", "do_C"):   # C is a clean cause: see == do
            m = mean_B + self.gamma * (value - mu_C)
            v = (self.lam_b ** 2 * self.sigma_u ** 2 + self.noise_scale ** 2)
        else:
            raise ValueError(query)
        return 1.0 - Phi((tau - m) / math.sqrt(max(v, 1e-9)))

    def p_spurious(self, x_ck: np.ndarray, query: str, tau: float,
                   value: float = 0.0) -> float:
        """The confounded forecaster: treats do(A) like see(A) (uses the
        biased A→B slope) and treats do(C)/see(C) correctly (C is a real
        cause). This is what pooled-OLS-on-observables predicts."""
        if query == "do_A":                          # the diagnostic error
            return self.p_star(x_ck, "see_A", tau, value)
        return self.p_star(x_ck, query, tau, value)

    def confound_gap(self, x_ck: np.ndarray, tau: float, value: float) -> float:
        """|correct do(A) − confounded do(A)| — the causal-necessity size."""
        return abs(self.p_star(x_ck, "do_A", tau, value)
                   - self.p_spurious(x_ck, "do_A", tau, value))


if __name__ == "__main__":
    # self-test: closed-form oracles vs Monte Carlo, for every query type
    rng = np.random.default_rng(0)
    worst = 0.0
    for seed in (300, 301, 302):
        scm = ConfoundedDynSCM(seed=seed)
        X = scm.simulate()
        x_ck = X[54]                                 # some observed row
        mean_B, var_B, mu_A, mu_C, beta = scm._forecast_moments(x_ck)
        var_A = scm.lam_a ** 2 * scm.sigma_u ** 2 + scm.noise_scale ** 2
        for query, value in (("obs", 0.0), ("see_A", mu_A + 1.0),
                             ("do_A", mu_A + 1.0), ("see_C", mu_C + 1.5),
                             ("do_C", mu_C + 1.5)):
            tau = mean_B + 0.3
            p = scm.p_star(x_ck, query, tau, value)
            # MC: draw next period under the query's regime
            N = 2_000_000
            u = rng.normal(0, scm.sigma_u, N)
            base = scm.base_mean(x_ck)
            noise = rng.normal(0, scm.noise_scale, (N, scm.n))
            Cnext = base[scm.C] + noise[:, scm.C]
            if query in ("see_C", "do_C"):
                Cnext = np.full(N, value)            # C set/observed at value
            Bnext = base[scm.B] + noise[:, scm.B] + scm.gamma * Cnext + scm.lam_b * u
            if query == "see_A":
                # condition on observing A = value via a kernel around it
                Anext = base[scm.A] + noise[:, scm.A] + scm.lam_a * u
                bw = 0.06 * math.sqrt(var_A)   # narrow: kernel bias << SE
                w = np.exp(-0.5 * ((Anext - value) / bw) ** 2)
                pm = float(np.average(Bnext > tau, weights=w))
                neff = w.sum() ** 2 / (w ** 2).sum()
            else:
                # obs / do_A / do_C: A is irrelevant to B; just marginalize
                pm = float(np.mean(Bnext > tau))
                neff = N
            err = abs(p - pm) / math.sqrt(max(pm * (1 - pm) / neff, 1e-12))
            worst = max(worst, err)
            print(f"  seed{seed} {query:>6}: exact={p:.3f} MC={pm:.3f} "
                  f"({err:.1f} SE, n_eff={neff:.0f})")
    print(f"\nworst |exact - MC| = {worst:.1f} SE (should be < ~4)")
