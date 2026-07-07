"""Exact event probabilities for linear-Gaussian SCMs (KNOWABLE_WORLDS_DESIGN §5).

For the linear SCM  X = c + Wᵀ·X + ε,  ε ~ N(0, σ²I), the joint is Gaussian:

    μ = (I − Wᵀ)⁻¹ c
    Σ = (I − Wᵀ)⁻¹ D (I − Wᵀ)⁻ᵀ,   D = diag(noise variances)

Hard interventions do(X_S = v) are handled structurally: zero the incoming
columns W[:, j] for j∈S, set c_j = v_j and noise var 0 — then the same formulas
apply. Event probabilities and threshold inversion are closed-form:

    P(X_k > τ)          = 1 − Φ((τ − μ_k)/√Σ_kk)
    τ  for target p*    = μ_k + √Σ_kk · Φ⁻¹(1 − p*)

`mc_event_prob` provides the simulation estimate used to (a) verify the
analytic module and (b) score tanh/nonlinear SCMs where no closed form exists.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from scm.engine import SCM  # noqa: E402


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _phi_inv(p: float) -> float:
    # Acklam-style rational approximation is overkill; use binary search on erf
    # (deterministic, no scipy dependency; |err| < 1e-10).
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def gaussian_moments(scm: SCM, do: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Exact (mean, covariance) of the linear-Gaussian SCM under hard do()."""
    if scm.functional != "linear":
        raise ValueError("analytic moments require functional='linear'")
    n = scm.n
    do = do or {}
    W = scm.W.copy()
    c = scm.intercept.astype(float).copy()
    noise_var = np.full(n, float(scm.noise_scale) ** 2)
    for j, v in do.items():
        W[:, j] = 0.0          # sever incoming edges
        c[j] = float(v)        # clamp
        noise_var[j] = 0.0
    M = np.linalg.inv(np.eye(n) - W.T)
    mu = M @ c
    Sigma = M @ np.diag(noise_var) @ M.T
    return mu, Sigma


def event_prob(scm: SCM, outcome_idx: int, tau: float, do: dict | None = None) -> float:
    """Exact P(X_outcome > tau [| do]) for a linear SCM."""
    mu, Sigma = gaussian_moments(scm, do)
    m, var = float(mu[outcome_idx]), float(Sigma[outcome_idx, outcome_idx])
    if var <= 1e-14:                     # deterministic (clamped) outcome
        return 1.0 if m > tau else 0.0
    return 1.0 - _phi((tau - m) / math.sqrt(var))


def tau_for_target(scm: SCM, outcome_idx: int, p_target: float,
                   do: dict | None = None) -> float:
    """Threshold tau such that P(X_outcome > tau | do) == p_target, exactly."""
    mu, Sigma = gaussian_moments(scm, do)
    var = float(Sigma[outcome_idx, outcome_idx])
    if var <= 1e-14:
        raise ValueError("outcome is deterministic under this intervention")
    return float(mu[outcome_idx]) + math.sqrt(var) * _phi_inv(1.0 - p_target)


def mc_event_prob(scm: SCM, outcome_idx: int, tau: float, do: dict | None = None,
                  n_samples: int = 200_000, seed: int = 123) -> float:
    """Simulation estimate (verification for linear; the truth engine for tanh)."""
    X = scm.sample(n_samples, do=do, seed=seed)
    return float((X[:, outcome_idx] > tau).mean())


def cond_prob(scm: SCM, outcome_idx: int, tau: float, given_idx: int,
              given_val: float) -> float:
    """OBSERVATIONAL P(X_outcome > tau | X_given = given_val) — the correlational
    answer, via exact Gaussian conditioning on the joint. For root interventions
    this equals the do() answer; for confounded non-root interventions it is the
    TRAP the causal answer must diverge from."""
    mu, Sigma = gaussian_moments(scm)
    sii = float(Sigma[given_idx, given_idx])
    if sii <= 1e-14:
        return event_prob(scm, outcome_idx, tau)
    m = float(mu[outcome_idx]) + float(Sigma[outcome_idx, given_idx]) / sii         * (given_val - float(mu[given_idx]))
    var = float(Sigma[outcome_idx, outcome_idx])         - float(Sigma[outcome_idx, given_idx]) ** 2 / sii
    if var <= 1e-14:
        return 1.0 if m > tau else 0.0
    return 1.0 - _phi((tau - m) / math.sqrt(var))


def counterfactual_value(scm: SCM, x_factual: np.ndarray, do: dict) -> np.ndarray:
    """Exact Pearl rung-3 counterfactual for a linear SCM (abduct -> act -> predict).

    1. ABDUCT: recover every noise term from the full factual realization:
           eps_j = x_j - c_j - sum_i W[i,j] * x_i
    2. ACT: sever incoming edges of the intervened nodes, clamp them to v.
    3. PREDICT: replay the SAME noise through the modified equations.
    With full factual evidence the counterfactual is DETERMINISTIC — the engine
    returns the exact vector the world would have produced.
    """
    if scm.functional != "linear":
        raise ValueError("exact counterfactuals implemented for linear SCMs")
    n = scm.n
    x = np.asarray(x_factual, dtype=float).reshape(n)
    eps = x - scm.intercept - scm.W.T @ x          # abduction
    W2 = scm.W.copy()
    c2 = scm.intercept.astype(float).copy()
    e2 = eps.copy()
    for j, v in do.items():
        W2[:, j] = 0.0
        c2[j] = float(v)
        e2[j] = 0.0                                # clamped node has no noise term
    return np.linalg.inv(np.eye(n) - W2.T) @ (c2 + e2)
