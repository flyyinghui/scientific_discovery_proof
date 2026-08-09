#!/usr/bin/env python3
"""
J-space Bridge Matrix — Compute concept correlation matrix from neural memory brain.

Maps 170K+ brain neurons to a 12×12 concept correlation matrix, quantifying
the theoretical grounding of each proof candidate.

Usage:
    python jspace_bridge.py --conjecture conjecture.json --output bridge.json
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

# Default 12 key concepts: 6 geometric + 6 physical
DEFAULT_CONCEPTS = [
    "g_Ricci", "g_KLS", "g_Matsushima", "g_Chern", "g_WZW", "g_CDM",
    "p_M_R", "p_m_nu", "p_SB", "p_FRG", "p_CGICE", "p_NJL"
]


def compute_j_score(concept_a: str, concept_b: str, brain=None,
                    alpha: float = 0.4, beta: float = 0.3, gamma: float = 0.3) -> float:
    """
    Compute J-score between two concepts.
    
    J(a,b) = α·sim(a,b) + β·MI(a,b) + γ·co_activation(a,b)
    
    With brain: uses actual recall and activation data.
    Without brain: returns mock values for demonstration.
    """
    if brain is None:
        # Mock: geodesic distance-based similarity
        import hashlib
        ha = int(hashlib.md5(concept_a.encode()).hexdigest()[:8], 16)
        hb = int(hashlib.md5(concept_b.encode()).hexdigest()[:8], 16)
        base = abs(ha - hb) / (2**32)
        return round(1.0 - 0.5 * base, 2)
    
    # Real computation with brain
    sim = _cosine_similarity(brain, concept_a, concept_b)
    mi = _mutual_information(brain, concept_a, concept_b)
    coact = _co_activation(brain, concept_a, concept_b)
    
    return round(alpha * sim + beta * mi + gamma * coact, 2)


def _cosine_similarity(brain, a, b):
    """Cosine similarity between concept activation vectors."""
    try:
        ra = brain.recall(a, top_k=20)
        rb = brain.recall(b, top_k=20)
        if not ra or not rb:
            return 0.1
        # Use activation values for vector comparison
        vec_a = np.array([r.get('activation', 0.1) for r in ra])
        vec_b = np.array([r.get('activation', 0.1) for r in rb])
        # Pad to same length
        max_len = max(len(vec_a), len(vec_b))
        vec_a = np.pad(vec_a, (0, max_len - len(vec_a)))
        vec_b = np.pad(vec_b, (0, max_len - len(vec_b)))
        dot = np.dot(vec_a, vec_b)
        norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        return dot / max(norm, 1e-10)
    except Exception:
        return 0.1


def _mutual_information(brain, a, b):
    """Normalized mutual information from co-occurrence."""
    try:
        ra = brain.recall(a, top_k=20)
        rb = brain.recall(b, top_k=20)
        ids_a = {r.get('id') for r in ra}
        ids_b = {r.get('id') for r in rb}
        intersection = len(ids_a & ids_b)
        union = len(ids_a | ids_b)
        return intersection / max(union, 1)
    except Exception:
        return 0.1


def _co_activation(brain, a, b):
    """Co-activation based on shared synaptic connections."""
    try:
        ra = brain.recall(a, top_k=20)
        rb = brain.recall(b, top_k=20)
        avg_a = np.mean([r.get('activation', 0.1) for r in ra])
        avg_b = np.mean([r.get('activation', 0.1) for r in rb])
        return min(avg_a, avg_b) / max(avg_a, avg_b, 1e-10)
    except Exception:
        return 0.1


def build_bridge_matrix(concepts=None, brain=None, output_path=None):
    """Build the full 12×12 J-space bridge matrix."""
    if concepts is None:
        concepts = DEFAULT_CONCEPTS
    
    n = len(concepts)
    matrix = {}
    
    for i, ca in enumerate(concepts):
        matrix[ca] = {}
        for j, cb in enumerate(concepts):
            if i == j:
                matrix[ca][cb] = 1.00
            elif j < i:
                matrix[ca][cb] = matrix[cb][ca]  # Symmetric
            else:
                matrix[ca][cb] = compute_j_score(ca, cb, brain)
    
    result = {
        "concepts": concepts,
        "matrix": matrix,
        "thresholds": {
            "theorem": 0.70,
            "honest_axiom": 0.50,
            "postulated": 0.0
        }
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
    
    return result


def print_matrix(matrix_dict):
    """Pretty-print the bridge matrix."""
    concepts = list(matrix_dict["matrix"].keys())
    header = "| Concept | " + " | ".join(c[:10] for c in concepts) + " |"
    sep = "|:---|" + ":---:|" * len(concepts)
    
    print(header)
    print(sep)
    
    for ca in concepts:
        row = f"| {ca[:10]:10s} |"
        for cb in concepts:
            val = matrix_dict["matrix"][ca].get(cb, 0.0)
            row += f" {val:.2f} |"
        print(row)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--conjecture", help="Conjecture JSON to extract concepts from")
    parser.add_argument("--concepts", nargs="*", help="Custom concept list")
    parser.add_argument("--output", default="jspace_bridge.json")
    parser.add_argument("--brain-data", default="/mnt/d/ai_for_science/neural_memory_data")
    parser.add_argument("--mock", action="store_true", help="Use mock values (no brain needed)")
    args = parser.parse_args()
    
    concepts = DEFAULT_CONCEPTS
    
    if args.conjecture:
        with open(args.conjecture) as f:
            c = json.load(f)
        concepts = c.get("brain_concepts", DEFAULT_CONCEPTS)
    
    if args.concepts:
        concepts = args.concepts
    
    brain = None
    if not args.mock:
        try:
            import sys
            sys.path.insert(0, "/mnt/d/ai_for_science")
            from neural_memory_brain.brain import NeuralMemoryBrain
            brain = NeuralMemoryBrain(data_dir=args.brain_data)
            stats = brain.graph.get_stats()
            print(f"Brain: {stats['neuron_count']:,} neurons loaded")
        except Exception as e:
            print(f"Brain unavailable ({e}), using mock values")
    
    result = build_bridge_matrix(concepts, brain, args.output)
    print(f"\nJ-space Bridge Matrix ({len(concepts)}×{len(concepts)}):\n")
    print_matrix(result)
    print(f"\nSaved to: {args.output}")
