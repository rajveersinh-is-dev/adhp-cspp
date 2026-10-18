# ALGORITHM SPECIFICATION: ADAPTIVE DUAL HULL PRUNING (ADHP)
## Exact & High-Performance Solvers for the Weight-Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/ALGORITHM_SPECIFICATION.md`  

---

### 1. Architectural Overview

The **ADHP** solver architecture provides two execution engines:
1. **Floating-Point Engine (`AdhpSolver`)**: Operates on standard real-valued IEEE 754 `f64` graphs under an explicit, certified $(\epsilon_{\text{feas}}, \epsilon_{\text{prune}})$-admissibility contract.
2. **Exact Integer Engine (`IntAdhpSolver`)**: Operates on `u64` integer graphs using checked integer arithmetic, rational dual multipliers $\lambda = p / q$, ceiling lower-bound evaluation, zero-tolerance feasibility, and strict Pareto dominance, achieving 100% mathematically exact zero-tolerance optimality.

Both engines execute through four tightly integrated, non-redundant phases:

```
[Phase 1: Backward-Centric Weight Preprocessing]
       │
       ▼
   Run Dijkstra on G^R from destination t with pure weight (w-only).
   Outputs:
     - dist_weight[u] for all u ∈ V (Filter 1 resource bounding)
     - d_w(s, t): If > W, certified INFEASIBLE immediately in 1 Dijkstra pass!
     - Suffix tree: Reconstructs path P_w(s, t) initializing C_UB = c(P_w)
       │
       ▼
[Phase 2: Backward-Centric Unconstrained Cost & Adaptive Facet Discovery]
       │
       ▼
   Run Dijkstra on G^R from t with λ₁ = 0 (c-only).
   Outputs:
     - dist_dual[0][u] = d_c(u, t) for all u ∈ V
     - Reconstructs P_c(s, t): If w(P_c) ≤ W, return globally OPTIMAL in 2 passes!
   If constrained, perform adaptive bisection:
     - For λ_mid = (c_r - c_l) / (w_l - w_r), run Dijkstra on G^R from t.
     - Single backward run computes BOTH path P_mid(s, t) (updating C_UB)
       AND full reverse distance array dist_dual[k].
     - Adaptive cutoff: Only adopt facet if root lower bound gain > 2%.
       │
       ▼
[Phase 3: Priority Search with Strict Pareto Dominance]
       │
       ▼
   Min-heap priority search from s with admissible key c + L_u^Λ(W - w).
   At each edge relaxation (u → v):
     Filter 1 (Feasibility): w + w_e + dist_weight[v] > W ⟹ PRUNE
     Filter 2 (Dual Hull):  c + c_e + L_v^Λ(rem_w) > C_UB + tol ⟹ PRUNE
     Filter 3 (Dominance):  Frontiers[v].is_dominated(new_c, new_w) ⟹ PRUNE
   If non-dominated, Frontiers[v].insert_and_prune(new_c, new_w) and push to heap.
```

---

### 2. Algorithms and Pseudocode

#### Algorithm 1: Backward-Centric Preprocessing & Adaptive Facet Discovery
```text
function ADHP_PREPROCESS(G, s, t, W, K_max):
    // Step 1: Backward tree on pure weight
    tree_w ← DijkstraBackwardTree(G, target=t, lambda=0, use_weight_only=true)
    if tree_w.dist[s] > W or tree_w.dist[s] == +∞:
        return (Infeasible, null)
        
    P_w ← tree_w.reconstruct_path(s, t)
    best_cost ← c(P_w)
    best_weight ← w(P_w)
    best_path ← P_w
    
    // Step 2: Backward tree on pure cost (lambda_1 = 0)
    tree_c ← DijkstraBackwardTree(G, target=t, lambda=0, use_weight_only=false)
    P_c ← tree_c.reconstruct_path(s, t)
    
    if w(P_c) ≤ W:
        // Unconstrained cost-minimal path satisfies budget -> globally optimal!
        return (EarlyOptimal, P_c)
        
    lambdas ← [0.0]
    dist_dual ← [tree_c.dist]
    
    // Step 3: Adaptive Bisection
    queue ← [(c(P_c), w(P_c), c(P_w), w(P_w))]
    
    while |lambdas| < K_max and not queue.isEmpty():
        (c_l, w_l, c_r, w_r) ← queue.pop_front()
        dw ← w_l - w_r
        dc ← c_r - c_l
        if dw ≤ 1e-9 or dc ≤ 1e-9:
            continue
            
        lambda_mid ← dc / dw
        if lambda_mid in lambdas:
            continue
            
        // Single backward pass computes path for C_UB AND reverse distance field
        tree_mid ← DijkstraBackwardTree(G, target=t, lambda=lambda_mid, use_weight_only=false)
        P_mid ← tree_mid.reconstruct_path(s, t)
        
        if w(P_mid) ≤ W and c(P_mid) < best_cost:
            best_cost ← c(P_mid)
            best_weight ← w(P_mid)
            best_path ← P_mid
            
        // Root lower bound marginal gain check
        root_lb_mid ← tree_mid.dist[s] - lambda_mid * W
        cur_root_lb ← max_{k} [dist_dual[k][s] - lambdas[k] * W]
        rel_gain ← (root_lb_mid - cur_root_lb) / max(1.0, |cur_root_lb|)
        
        if rel_gain > 0.02:
            lambdas.append(lambda_mid)
            dist_dual.append(tree_mid.dist)
            if w_l - w(P_mid) > 1e-6 and c(P_mid) - c_l > 1e-6:
                queue.push((c_l, w_l, c(P_mid), w(P_mid)))
            if w(P_mid) - w_r > 1e-6 and c_r - c(P_mid) > 1e-6:
                queue.push((c(P_mid), w(P_mid), c_r, w_r))
                
    return (Ready, lambdas, dist_dual, tree_w.dist, best_cost, best_path)
```

---

#### Algorithm 2: Strict Pareto Frontier Maintenance
```text
class VertexFrontier:
    points: Array of (cost, weight) sorted strictly by weight ascending
    
    function IS_DOMINATED(new_c, new_w):
        if points is empty:
            return false
            
        // Binary search: pos is the index of first point with weight > new_w
        pos ← partition_point(points, pt => pt.weight ≤ new_w)
        if pos > 0:
            // Point at pos - 1 has maximum weight ≤ new_w, hence minimum cost
            return points[pos - 1].cost ≤ new_c
        return false

    function INSERT_AND_PRUNE(new_c, new_w):
        // Remove existing points weakly dominated by (new_c, new_w)
        points.retain(pt => not (new_w ≤ pt.weight and new_c ≤ pt.cost))
        
        // Insert maintaining sorted order by weight ascending
        pos ← partition_point(points, pt => pt.weight < new_w)
        points.insert(pos, (new_c, new_w))
```

---

#### Algorithm 3: Priority Queue Search Loop
```text
function ADHP_SOLVE(G, s, t, W, K_max=5):
    prep_result ← ADHP_PREPROCESS(G, s, t, W, K_max)
    if prep_result is Infeasible:
        return Infeasible
    if prep_result is EarlyOptimal:
        return Solution(prep_result.path)
        
    (lambdas, dist_dual, dist_weight, C_UB, best_path) ← prep_result
    
    PQ ← MinHeap()
    Frontiers ← Array of VertexFrontier[|V|]
    
    root_lb ← max_k [dist_dual[k][s] - lambdas[k] * W]
    PQ.push(Label(vertex=s, cost=0.0, weight=0.0), key=root_lb)
    Frontiers[s].INSERT_AND_PRUNE(0.0, 0.0)
    
    while not PQ.isEmpty():
        curr ← PQ.pop()
        u ← curr.vertex
        c_u ← curr.cost
        w_u ← curr.weight
        
        if u == t:
            if w_u ≤ W + tol_feas and c_u < C_UB:
                C_UB ← c_u
                best_path ← curr.path
            continue
            
        prune_tol ← max(1.0, |C_UB|) * 1e-9
        lb_u ← max_k [dist_dual[k][u] - lambdas[k] * (W - w_u)]
        if c_u + lb_u > C_UB + prune_tol:
            continue
            
        for edge (u → v, cost c_e, weight w_e) in G.out_edges(u):
            new_c ← c_u + c_e
            new_w ← w_u + w_e
            
            // Filter 1: Resource feasibility
            if new_w + dist_weight[v] > W + tol_feas:
                continue
                
            // Filter 2: Dual Hull Pruning
            rem_w ← W - new_w
            lb_v ← max_k [dist_dual[k][v] - lambdas[k] * rem_w]
            if new_c + lb_v > C_UB + prune_tol:
                continue
                
            // Filter 3: Strict Pareto Dominance
            if Frontiers[v].IS_DOMINATED(new_c, new_w):
                continue
                
            Frontiers[v].INSERT_AND_PRUNE(new_c, new_w)
            PQ.push(Label(vertex=v, cost=new_c, weight=new_w), key=new_c + lb_v)
            
    if best_path is not null:
        return Solution(best_path, cost=C_UB, weight=w(best_path))
    else:
        return Infeasible
```
