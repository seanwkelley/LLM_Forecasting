"""
Semantic graph matching via embeddings + Hungarian algorithm.

Embeds DAG node descriptions with text-embedding-3-large, then uses
bipartite matching to align nodes across two graphs. Computes:
  - Semantic node Jaccard (matched pairs above cosine threshold / union)
  - Node-mapped edge Jaccard (edges matched via aligned endpoints)
  - Direct edge embedding Jaccard (embed edge descriptions, match directly)

Caches all embeddings to disk to avoid redundant API calls.

Usage:
    from forecast_bench.semantic_graph_match import semantic_graph_similarity
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
NODE_EMB_CACHE = CAUSAL_DIR / "node_embeddings.npz"
NODE_EMB_KEYS_CACHE = CAUSAL_DIR / "node_embeddings_keys.json"
EDGE_EMB_CACHE = CAUSAL_DIR / "edge_embeddings.npz"
EDGE_EMB_KEYS_CACHE = CAUSAL_DIR / "edge_embeddings_keys.json"


# ── API ──────────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    return api_key


def _get_embedding(text: str, api_key: str, max_retries: int = 3) -> list[float] | None:
    import time as _time
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": "openai/text-embedding-3-large", "input": text[:8000]},
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
            elif resp.status_code == 429:
                wait = 2 ** attempt
                print(f"  Rate limited, waiting {wait}s...")
                _time.sleep(wait)
                continue
            else:
                print(f"  Embedding API error: {resp.status_code}")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                _time.sleep(1)
                continue
            print(f"  Embedding error after {max_retries} retries: {e}")
            return None
    return None


# ── Cache ────────────────────────────────────────────────────────────────

def _load_cache(npz_path: Path, keys_path: Path) -> tuple[dict[str, int], np.ndarray | None]:
    if npz_path.exists() and keys_path.exists():
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
        data = np.load(str(npz_path))
        matrix = data["embeddings"]
        key_to_idx = {k: i for i, k in enumerate(keys)}
        return key_to_idx, matrix
    return {}, None


def _save_cache(key_to_idx: dict[str, int], matrix: np.ndarray,
                npz_path: Path, keys_path: Path):
    keys = [""] * len(key_to_idx)
    for k, i in key_to_idx.items():
        keys[i] = k
    # Write to temp files first, then rename to prevent corruption
    tmp_keys = keys_path.with_suffix(".json.tmp")
    # np.savez_compressed appends .npz if not present, so use .tmp suffix before .npz
    tmp_npz = npz_path.parent / (npz_path.stem + "_tmp.npz")
    tmp_keys.write_text(json.dumps(keys), encoding="utf-8")
    np.savez_compressed(str(tmp_npz), embeddings=matrix.astype(np.float32))
    import shutil
    shutil.move(str(tmp_keys), str(keys_path))
    shutil.move(str(tmp_npz), str(npz_path))


def _ensure_embeddings(texts_by_key: dict[str, str],
                       npz_path: Path, keys_path: Path,
                       api_key: str) -> tuple[dict[str, int], np.ndarray]:
    """Return (key_to_idx, matrix) with all requested keys embedded."""
    key_to_idx, matrix = _load_cache(npz_path, keys_path)

    missing = {k: t for k, t in texts_by_key.items() if k not in key_to_idx}
    if not missing:
        return key_to_idx, matrix

    print(f"  Embedding {len(missing)} new texts (cache has {len(key_to_idx)})...")
    new_keys, new_vecs = [], []
    for i, (k, text) in enumerate(missing.items()):
        emb = _get_embedding(text, api_key)
        if emb:
            new_keys.append(k)
            new_vecs.append(emb)
        if (i + 1) % 20 == 0:
            time.sleep(0.5)
        # Incremental save every 50 embeddings
        if len(new_vecs) > 0 and len(new_vecs) % 50 == 0:
            new_matrix = np.array(new_vecs, dtype=np.float32)
            if matrix is not None:
                matrix = np.vstack([matrix, new_matrix])
            else:
                matrix = new_matrix
            offset = len(key_to_idx)
            for j, k2 in enumerate(new_keys):
                key_to_idx[k2] = offset + j
            _save_cache(key_to_idx, matrix, npz_path, keys_path)
            print(f"    checkpoint: {len(key_to_idx)} embeddings saved")
            new_keys, new_vecs = [], []

    if new_vecs:
        new_matrix = np.array(new_vecs, dtype=np.float32)
        if matrix is not None:
            matrix = np.vstack([matrix, new_matrix])
        else:
            matrix = new_matrix
        offset = len(key_to_idx)
        for j, k in enumerate(new_keys):
            key_to_idx[k] = offset + j
        _save_cache(key_to_idx, matrix, npz_path, keys_path)
        print(f"  Cache updated: {len(key_to_idx)} total embeddings")

    return key_to_idx, matrix


# ── Cosine similarity ────────────────────────────────────────────────────

def _cosine_matrix(vecs_a: np.ndarray, vecs_b: np.ndarray) -> np.ndarray:
    """Cosine similarity matrix (n x m) between two sets of vectors."""
    norm_a = vecs_a / (np.linalg.norm(vecs_a, axis=1, keepdims=True) + 1e-10)
    norm_b = vecs_b / (np.linalg.norm(vecs_b, axis=1, keepdims=True) + 1e-10)
    return norm_a @ norm_b.T


# ── Matching ─────────────────────────────────────────────────────────────

def _hungarian_match(sim_matrix: np.ndarray, threshold: float = 0.7
                     ) -> list[tuple[int, int, float]]:
    """Bipartite matching maximizing similarity. Returns matched (i, j, sim) pairs above threshold."""
    cost = 1.0 - sim_matrix
    row_ind, col_ind = linear_sum_assignment(cost)
    matches = []
    for r, c in zip(row_ind, col_ind):
        s = sim_matrix[r, c]
        if s >= threshold:
            matches.append((r, c, float(s)))
    return matches


def semantic_node_jaccard(nodes1: list[dict], nodes2: list[dict],
                          key_to_idx: dict[str, int], matrix: np.ndarray,
                          model1: str, model2: str, qid: str,
                          threshold: float = 0.7
                          ) -> tuple[float, dict[str, str]]:
    """
    Semantic Jaccard over nodes using embedding-based Hungarian matching.

    Returns:
        (jaccard_score, node_mapping)  where node_mapping maps node IDs from
        graph1 to matched node IDs in graph2.
    """
    if not nodes1 and not nodes2:
        return 1.0, {}
    if not nodes1 or not nodes2:
        return 0.0, {}

    def _get_vecs(nodes, model):
        keys = [f"node|{qid}|{model}|{n['id']}" for n in nodes]
        idxs = [key_to_idx[k] for k in keys if k in key_to_idx]
        if len(idxs) != len(nodes):
            return None
        return matrix[idxs]

    vecs1 = _get_vecs(nodes1, model1)
    vecs2 = _get_vecs(nodes2, model2)
    if vecs1 is None or vecs2 is None:
        return 0.0, {}

    sim = _cosine_matrix(vecs1, vecs2)
    matches = _hungarian_match(sim, threshold)

    matched_count = len(matches)
    union = len(nodes1) + len(nodes2) - matched_count
    jaccard = matched_count / union if union > 0 else 0.0

    node_map = {}
    for r, c, _ in matches:
        node_map[nodes1[r]["id"]] = nodes2[c]["id"]

    return jaccard, node_map


def mapped_edge_jaccard(edges1: list[dict], edges2: list[dict],
                        node_map: dict[str, str]) -> float:
    """Edge Jaccard using node alignment from semantic matching."""
    if not edges1 and not edges2:
        return 1.0
    if not edges1 or not edges2:
        return 0.0

    # Map edges from graph1 into graph2's node namespace
    mapped_edges1 = set()
    for e in edges1:
        src = node_map.get(e["from"])
        tgt = node_map.get(e["to"])
        if src and tgt:
            mapped_edges1.add((src, tgt))

    edges2_set = {(e["from"], e["to"]) for e in edges2}

    matched = len(mapped_edges1 & edges2_set)
    union = len(mapped_edges1 | edges2_set)
    return matched / union if union > 0 else 0.0


def semantic_edge_jaccard(edges1: list[dict], edges2: list[dict],
                           nodes1: list[dict], nodes2: list[dict],
                           key_to_idx: dict[str, int], matrix: np.ndarray,
                           model1: str, model2: str, qid: str,
                           threshold: float = 0.7) -> float:
    """Direct edge embedding Jaccard via Hungarian matching on edge descriptions."""
    if not edges1 and not edges2:
        return 1.0
    if not edges1 or not edges2:
        return 0.0

    def _get_edge_vecs(edges, model):
        keys = [f"edge|{qid}|{model}|{e['from']}|{e['to']}" for e in edges]
        idxs = [key_to_idx.get(k) for k in keys]
        if any(i is None for i in idxs):
            return None
        return matrix[np.array(idxs)]

    vecs1 = _get_edge_vecs(edges1, model1)
    vecs2 = _get_edge_vecs(edges2, model2)
    if vecs1 is None or vecs2 is None:
        return 0.0

    sim = _cosine_matrix(vecs1, vecs2)
    matches = _hungarian_match(sim, threshold)

    matched_count = len(matches)
    union = len(edges1) + len(edges2) - matched_count
    return matched_count / union if union > 0 else 0.0


# ── Public interface ─────────────────────────────────────────────────────

def build_embedding_texts(question_data: dict[str, dict],
                          model_name: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build {cache_key: text_to_embed} dicts for all nodes and edges in a model's data.
    """
    node_texts = {}
    edge_texts = {}
    for qid, qdata in question_data.items():
        for n in qdata.get("nodes", []):
            key = f"node|{qid}|{model_name}|{n['id']}"
            desc = n.get("description", n["id"])
            node_texts[key] = f"{n['id']}: {desc}"
        for e in qdata.get("edges", []):
            key = f"edge|{qid}|{model_name}|{e['from']}|{e['to']}"
            mechanism = e.get("mechanism", f"{e['from']} -> {e['to']}")
            edge_texts[key] = f"{e['from']} -> {e['to']}: {mechanism}"
    return node_texts, edge_texts


def ensure_all_embeddings(runs: dict[str, tuple],
                          api_key: str | None = None
                          ) -> tuple[dict[str, int], np.ndarray,
                                     dict[str, int], np.ndarray]:
    """
    Embed all nodes and edges across all models. Returns node and edge caches.

    Args:
        runs: {model_name: (rows, question_data)} from load_causal_results / load_question_jsons
        api_key: OpenRouter API key (auto-detected if None)
    """
    if api_key is None:
        api_key = _get_api_key()
    if not api_key:
        raise ValueError("No OPENROUTER_API_KEY found")

    all_node_texts = {}
    all_edge_texts = {}
    for model_name, (_, qdata) in runs.items():
        nt, et = build_embedding_texts(qdata, model_name)
        all_node_texts.update(nt)
        all_edge_texts.update(et)

    print(f"Node texts: {len(all_node_texts)}, Edge texts: {len(all_edge_texts)}")

    node_idx, node_mat = _ensure_embeddings(
        all_node_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key)
    edge_idx, edge_mat = _ensure_embeddings(
        all_edge_texts, EDGE_EMB_CACHE, EDGE_EMB_KEYS_CACHE, api_key)

    return node_idx, node_mat, edge_idx, edge_mat


def _aligned_spectral_distance(nodes1, edges1, nodes2, edges2, node_map):
    """Spectral distance on graphs aligned to a unified node namespace.

    Builds adjacency matrices over the union of matched + unmatched nodes,
    using the Hungarian node_map to place both graphs in the same space.
    """
    # Build unified node namespace: matched nodes share a slot,
    # unmatched nodes each get their own slot.
    ids1 = {n["id"] for n in nodes1}
    ids2 = {n["id"] for n in nodes2}
    inv_map = {v: k for k, v in node_map.items()}  # graph2 id -> graph1 id

    # Canonical names: for matched pairs use graph1's id as canonical
    # For unmatched graph2 nodes, prefix to avoid collisions
    unified = set()
    g1_canon = {}  # graph1 id -> canonical
    g2_canon = {}  # graph2 id -> canonical

    for nid in ids1:
        g1_canon[nid] = nid
        unified.add(nid)

    for nid in ids2:
        if nid in inv_map:
            # This graph2 node matched to a graph1 node
            g2_canon[nid] = inv_map[nid]
        else:
            canon = f"_g2_{nid}"
            g2_canon[nid] = canon
            unified.add(canon)

    node_list = sorted(unified)
    idx = {n: i for i, n in enumerate(node_list)}
    n = len(node_list)
    if n == 0:
        return 0.0

    def _build_adj(edges, canon_map):
        adj = np.zeros((n, n))
        for e in edges:
            u = canon_map.get(e["from"])
            v = canon_map.get(e["to"])
            if u and v and u in idx and v in idx:
                adj[idx[u], idx[v]] = 1
                adj[idx[v], idx[u]] = 1
        return adj

    def _spectrum(adj):
        deg_vals = adj.sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            d_inv_sqrt = np.diag(
                np.where(deg_vals > 0, 1.0 / np.sqrt(deg_vals), 0))
        norm_lap = np.eye(n) - d_inv_sqrt @ adj @ d_inv_sqrt
        return np.sort(np.real(np.linalg.eigvals(norm_lap)))

    spec1 = _spectrum(_build_adj(
        [{"from": e["from"], "to": e["to"]} for e in edges1], g1_canon))
    spec2 = _spectrum(_build_adj(
        [{"from": e["from"], "to": e["to"]} for e in edges2], g2_canon))

    return float(np.linalg.norm(spec1 - spec2))


def _semantic_scores_for_pair(
    nodes1: list[dict], edges1: list[dict],
    nodes2: list[dict], edges2: list[dict],
    node_idx: dict[str, int], node_mat: np.ndarray,
    edge_idx: dict[str, int], edge_mat: np.ndarray,
    model1: str, model2: str,
    qid1: str, qid2: str,
    threshold: float = 0.7,
) -> tuple[float, float, float, float]:
    """Compute all three semantic Jaccards + aligned spectral distance for a single graph pair.

    qid1/qid2 are the question IDs used to look up embeddings (they differ
    during permutation tests when we pair mismatched questions).

    Returns (node_jaccard, mapped_edge_jaccard, direct_edge_jaccard, spectral_dist).
    """
    if not nodes1 and not nodes2:
        return 1.0, 1.0, 1.0, 0.0
    if not nodes1 or not nodes2:
        return 0.0, 0.0, 0.0, 0.0

    def _get_node_vecs(nodes, model, qid):
        keys = [f"node|{qid}|{model}|{n['id']}" for n in nodes]
        idxs = [node_idx.get(k) for k in keys]
        if any(i is None for i in idxs):
            return None
        return node_mat[np.array(idxs)]

    vecs1 = _get_node_vecs(nodes1, model1, qid1)
    vecs2 = _get_node_vecs(nodes2, model2, qid2)
    if vecs1 is None or vecs2 is None:
        return 0.0, 0.0, 0.0, 0.0

    sim = _cosine_matrix(vecs1, vecs2)
    matches = _hungarian_match(sim, threshold)
    matched_count = len(matches)
    union_n = len(nodes1) + len(nodes2) - matched_count
    nj = matched_count / union_n if union_n > 0 else 0.0

    # Node map for mapped edge Jaccard and aligned spectral distance
    node_map = {nodes1[r]["id"]: nodes2[c]["id"] for r, c, _ in matches}
    mej = mapped_edge_jaccard(edges1, edges2, node_map)

    # Aligned spectral distance
    sd = _aligned_spectral_distance(nodes1, edges1, nodes2, edges2, node_map)

    # Direct edge embedding Jaccard
    def _get_edge_vecs(edges, model, qid):
        keys = [f"edge|{qid}|{model}|{e['from']}|{e['to']}" for e in edges]
        idxs = [edge_idx.get(k) for k in keys]
        if any(i is None for i in idxs):
            return None
        return edge_mat[np.array(idxs)]

    evecs1 = _get_edge_vecs(edges1, model1, qid1)
    evecs2 = _get_edge_vecs(edges2, model2, qid2)
    if evecs1 is None or evecs2 is None:
        dej = 0.0
    elif len(edges1) == 0 and len(edges2) == 0:
        dej = 1.0
    elif len(edges1) == 0 or len(edges2) == 0:
        dej = 0.0
    else:
        esim = _cosine_matrix(evecs1, evecs2)
        ematches = _hungarian_match(esim, threshold)
        ematched = len(ematches)
        eunion = len(edges1) + len(edges2) - ematched
        dej = ematched / eunion if eunion > 0 else 0.0

    return nj, mej, dej, sd


def compute_semantic_similarity(
    qdata1: dict[str, dict], qdata2: dict[str, dict],
    model1: str, model2: str,
    node_idx: dict[str, int], node_mat: np.ndarray,
    edge_idx: dict[str, int], edge_mat: np.ndarray,
    threshold: float = 0.7,
    n_perm: int = 5000,
    seed: int = 42,
) -> dict:
    """
    Compute per-question semantic Jaccard (node, mapped-edge, direct-edge)
    between two models' DAGs, with permutation p-values.

    Returns dict with observed means, per-question scores, and p-values.
    """
    shared = sorted(set(qdata1.keys()) & set(qdata2.keys()))
    n_sh = len(shared)

    # Pre-extract nodes/edges per question
    nodes_list1 = [qdata1[qid].get("nodes", []) for qid in shared]
    nodes_list2 = [qdata2[qid].get("nodes", []) for qid in shared]
    edges_list1 = [qdata1[qid].get("edges", []) for qid in shared]
    edges_list2 = [qdata2[qid].get("edges", []) for qid in shared]

    # Observed scores
    node_jaccards = []
    mapped_edge_jaccards = []
    direct_edge_jaccards = []
    spectral_dists = []

    for k, qid in enumerate(shared):
        nj, mej, dej, sd = _semantic_scores_for_pair(
            nodes_list1[k], edges_list1[k],
            nodes_list2[k], edges_list2[k],
            node_idx, node_mat, edge_idx, edge_mat,
            model1, model2, qid, qid, threshold)
        node_jaccards.append(nj)
        mapped_edge_jaccards.append(mej)
        direct_edge_jaccards.append(dej)
        spectral_dists.append(sd)

    obs_nj = float(np.mean(node_jaccards))
    obs_mej = float(np.mean(mapped_edge_jaccards))
    obs_dej = float(np.mean(direct_edge_jaccards))
    obs_sd = float(np.mean(spectral_dists))

    # Permutation test: shuffle question pairings
    rng = np.random.default_rng(seed)
    perm_nj = np.zeros(n_perm)
    perm_mej = np.zeros(n_perm)
    perm_dej = np.zeros(n_perm)
    perm_sd = np.zeros(n_perm)

    for p in range(n_perm):
        pidx = rng.permutation(n_sh)
        p_nj, p_mej, p_dej, p_sd = [], [], [], []
        for k in range(n_sh):
            j = pidx[k]
            nj, mej, dej, sd = _semantic_scores_for_pair(
                nodes_list1[k], edges_list1[k],
                nodes_list2[j], edges_list2[j],
                node_idx, node_mat, edge_idx, edge_mat,
                model1, model2, shared[k], shared[j], threshold)
            p_nj.append(nj)
            p_mej.append(mej)
            p_dej.append(dej)
            p_sd.append(sd)
        perm_nj[p] = np.mean(p_nj)
        perm_mej[p] = np.mean(p_mej)
        perm_dej[p] = np.mean(p_dej)
        perm_sd[p] = np.mean(p_sd)
        if (p + 1) % 1000 == 0:
            print(f"    perm {p+1}/{n_perm}")

    pval_nj = float(np.mean(perm_nj >= obs_nj))
    pval_mej = float(np.mean(perm_mej >= obs_mej))
    pval_dej = float(np.mean(perm_dej >= obs_dej))
    pval_sd = float(np.mean(perm_sd <= obs_sd))  # lower spectral = more similar

    return {
        "n_shared": n_sh,
        "node_jaccard": node_jaccards,
        "mapped_edge_jaccard": mapped_edge_jaccards,
        "direct_edge_jaccard": direct_edge_jaccards,
        "spectral_distance": spectral_dists,
        "mean_node_jaccard": obs_nj,
        "mean_mapped_edge_jaccard": obs_mej,
        "mean_direct_edge_jaccard": obs_dej,
        "mean_spectral_distance": obs_sd,
        "pval_node_jaccard": pval_nj,
        "pval_mapped_edge_jaccard": pval_mej,
        "pval_direct_edge_jaccard": pval_dej,
        "pval_spectral_distance": pval_sd,
    }


def semantic_jaccard_pair(
    nodes1: list[dict], nodes2: list[dict],
    edges1: list[dict] | None = None, edges2: list[dict] | None = None,
    condition1: str = "a", condition2: str = "b",
    qid: str = "q",
    threshold: float = 0.7,
    api_key: str | None = None,
) -> dict:
    """Compute semantic Jaccard for a single pair of graphs (e.g., original vs augmented).

    Embeds nodes (and optionally edges) on the fly, using the shared cache.
    Suitable for within-model comparisons like spurious context or superforecasting.

    Returns dict with node_jaccard, mapped_edge_jaccard, and spectral_distance.
    """
    if api_key is None:
        api_key = _get_api_key()

    # Build embedding texts with condition-specific keys
    node_texts = {}
    for n in nodes1:
        key = f"node|{qid}|{condition1}|{n['id']}"
        node_texts[key] = f"{n['id']}: {n.get('description', n['id'])}"
    for n in nodes2:
        key = f"node|{qid}|{condition2}|{n['id']}"
        node_texts[key] = f"{n['id']}: {n.get('description', n['id'])}"

    node_idx, node_mat = _ensure_embeddings(
        node_texts, NODE_EMB_CACHE, NODE_EMB_KEYS_CACHE, api_key)

    # Get vectors
    def _vecs(nodes, cond):
        keys = [f"node|{qid}|{cond}|{n['id']}" for n in nodes]
        idxs = [node_idx.get(k) for k in keys]
        if any(i is None for i in idxs):
            return None
        return node_mat[np.array(idxs)]

    v1 = _vecs(nodes1, condition1)
    v2 = _vecs(nodes2, condition2)

    if v1 is None or v2 is None or len(nodes1) == 0 or len(nodes2) == 0:
        return {"node_jaccard": 0.0, "mapped_edge_jaccard": 0.0, "spectral_distance": 0.0}

    sim = _cosine_matrix(v1, v2)
    matches = _hungarian_match(sim, threshold)
    matched = len(matches)
    union = len(nodes1) + len(nodes2) - matched
    nj = matched / union if union > 0 else 0.0

    node_map = {nodes1[r]["id"]: nodes2[c]["id"] for r, c, _ in matches}

    # Mapped edge Jaccard
    mej = 0.0
    if edges1 is not None and edges2 is not None:
        mej = mapped_edge_jaccard(edges1, edges2, node_map)

    # Aligned spectral distance
    sd = 0.0
    if edges1 is not None and edges2 is not None:
        sd = _aligned_spectral_distance(nodes1, edges1, nodes2, edges2, node_map)

    return {"node_jaccard": nj, "mapped_edge_jaccard": mej, "spectral_distance": sd}
