from typing import List, Tuple, Dict
import math

def topk_indices(vec, k=3):
    return sorted(range(len(vec)), key=lambda i: vec[i], reverse=True)[:k]

def jaccard_topk(a: List[float], b: List[float], k=3) -> float:
    A, B = set(topk_indices(a,k)), set(topk_indices(b,k))
    return len(A & B)/max(1, len(A | B))

def overlap_matrix(skill_matrix: List[List[float]], k=3) -> List[List[float]]:
    n = len(skill_matrix)
    M = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1,n):
            s = jaccard_topk(skill_matrix[i], skill_matrix[j], k=k)
            M[i][j]=M[j][i]=s
    return M

def gap_suggestions(demand_vec: List[float], capacity_vec: List[float], taxonomy: List[str]) -> List[str]:
    out = []
    for i,(d,c) in enumerate(zip(demand_vec, capacity_vec)):
        if c == 0 and d > 0:
            out.append(f"Zero capacity on '{taxonomy[i]}' — spin up micro-agent or cross-train.")
        elif c > 0 and d/c > 1.6:  # demand 60% over capacity
            out.append(f"Shortfall on '{taxonomy[i]}' — increase allocation or create auxiliary specialization.")
    return out