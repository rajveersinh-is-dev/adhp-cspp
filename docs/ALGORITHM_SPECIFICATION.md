# ALGORITHM SPECIFICATION: ADAPTIVE DUAL HULL PRUNING (ADHP)
## Exact Solver for the Weight-Constrained Shortest Path Problem

**Author**: Rajveersinh Vishal Pardeshi  
**Date**: October 2026  
**Document**: `docs/ALGORITHM_SPECIFICATION.md`  

---

### 1. Architectural Overview

The **ADHP** algorithm solves the Weight-Constrained Shortest Path Problem (CSPP) through four integrated phases:

```
[Phase 1: Adaptive Dual Discovery]
       │
       ▼
   Select K optimal multipliers Λ = {λ₁, ..., λ_K} via bisection on (s, t)
       │
       ▼
[Phase 2: Reverse Multi-Tree Preprocessing]
       │
       ▼
   Compute K backward Dijkstra trees from t on reversed graph G^R
   Store table: dist_dual[k][u] = d_{λ_k}(u, t) for all k ∈ [1, K], u ∈ V
       │
       ▼
[Phase 3: Root Feasibility & Upper Bound Initialization]
       │
       ▼
   Check d_w(s, t) ≤ W (feasibility check)
   Extract candidate feasible paths from backward trees to initialize C_UB
       │
       ▼
[Phase 4: Dual-Envelope Filtered Label Setting Search]
       │
       ▼
   Priority search from s to t maintaining Pareto frontier at each vertex
   For each candidate label (u, c, w):
       1. Resource check: w + d_w(u, t) > W ⟹ DROP
       2. Dual Envelope check: c + L_u^Λ(W - w) ≥ C_UB ⟹ DROP
       3. Local Pareto dominance check against VertexFrontier[u] ⟹ DROP or INSERT
```

---

### 2. Detailed Pseudocode

#### Algorithm 1: Adaptive Dual Multiplier Discovery
```text
function DISCOVER_DUAL_MULTIPLIERS(G, s, t, W, K_max):
    // Step 1: Solve extreme points
    P_c ← ShortestPath(G, s, t, cost=c)
    if P_c is null:
        return Infeasible
    if w(P_c) ≤ W:
        return Optimal(P_c, cost=c(P_c)) // Unconstrained path is feasible
        
    P_w ← ShortestPath(G, s, t, cost=w)
    if P_w is null or w(P_w) > W:
        return Infeasible // Even minimum weight path exceeds budget
        
    // Extreme multipliers: λ_1 = 0 (pure cost), λ_end = ∞ (pure weight)
    Λ ← [0.0]
    queue ← PriorityQueue() // Order by potential gap: (c(P_w) - c(P_c))
    
    initial_slope ← (c(P_w) - c(P_c)) / (w(P_c) - w(P_w))
    queue.push(segment=(P_c, P_w, initial_slope))
    
    while |Λ| < K_max and not queue.isEmpty():
        (P_left, P_right, λ_mid) ← queue.pop()
        
        // Solve shortest path with composite metric c + λ_mid * w
        P_mid ← ShortestPath(G, s, t, cost=c + λ_mid * w)
        
        // Check if P_mid represents a genuine new extreme point on the lower hull
        if P_mid != P_left and P_mid != P_right:
            Λ.append(λ_mid)
            if w(P_left) > w(P_mid) and c(P_mid) > c(P_left):
                s1 ← (c(P_mid) - c(P_left)) / (w(P_left) - w(P_mid))
                queue.push((P_left, P_mid, s1))
            if w(P_mid) > w(P_right) and c(P_right) > c(P_mid):
                s2 ← (c(P_right) - c(P_mid)) / (w(P_mid) - w(P_right))
                queue.push((P_mid, P_right, s2))
                
    sort(Λ) // Ensure λ_1 < λ_2 < ... < λ_K
    return Λ
```

---

#### Algorithm 2: Reverse Multi-Tree Preprocessing
```text
function PREPROCESS_REVERSE_TREES(G, t, Λ):
    K ← |Λ|
    n ← |V|
    dist_dual ← 2D Array of size [K][n], initialized to +∞
    G_rev ← ReverseGraph(G)
    
    for k from 1 to K:
        λ_k ← Λ[k]
        // Run Dijkstra from destination t on reversed graph using edge weight c_e + λ_k * w_e
        dist_dual[k] ← Dijkstra(G_rev, source=t, edge_weight=(c + λ_k * w))
        
    // Also store pure weight distance from t
    dist_weight ← Dijkstra(G_rev, source=t, edge_weight=w)
    
    return (dist_dual, dist_weight)
```

---

#### Algorithm 3: Dual Lower-Bound Envelope Evaluation
```text
function EVAL_DUAL_LOWER_BOUND(u, remaining_weight, Λ, dist_dual):
    max_lb ← -∞
    K ← |Λ|
    for k from 1 to K:
        val ← dist_dual[k][u] - Λ[k] * remaining_weight
        if val > max_lb:
            max_lb ← val
    return max_lb
```

*Note on binary search optimization*: Since the values $f_k(\Delta w) = d_{\lambda_k}(u, t) - \lambda_k \Delta w$ have slopes $-\lambda_k$ that are strictly decreasing ($\lambda_1 < \lambda_2 < \dots < \lambda_K$), the index attaining the maximum is unimodal. For larger $K \ge 16$, a ternary search or convex upper hull binary search computes the maximum in $O(\log K)$ time. For practical $K \in \{3, 5, 8\}$, an unrolled linear loop exhibits superior SIMD and cache locality.

---

#### Algorithm 4: Pareto Frontier Maintenance and Dominance Check
```text
class ParetoFrontier:
    labels: List of pairs (cost, weight) sorted by weight ascending

    function IS_DOMINATED(new_c, new_w):
        // Since list is sorted by weight ascending:
        // Any existing label with weight ≤ new_w must have cost < new_c,
        // otherwise it would dominate the new label.
        for each (c, w) in labels:
            if w ≤ new_w and c ≤ new_c:
                return true
            if w > new_w:
                break // No subsequent label can have smaller weight
        return false

    function INSERT_AND_PRUNE(new_c, new_w):
        // Remove existing labels that are dominated by (new_c, new_w):
        // A label with w ≥ new_w and c ≥ new_c is dominated.
        filtered ← []
        for each (c, w) in labels:
            if not (w ≥ new_w and c ≥ new_c):
                filtered.append((c, w))
        filtered.insert_sorted((new_c, new_w))
        labels ← filtered
```

---

#### Algorithm 5: ADHP Search Loop
```text
function ADHP_SOLVE(G, s, t, W, K_max=5):
    // Phase 1: Dual Discovery
    Λ ← DISCOVER_DUAL_MULTIPLIERS(G, s, t, W, K_max)
    if Λ is Infeasible:
        return NoSolution
    if Λ is Optimal:
        return EarlySolution
        
    // Phase 2: Reverse Multi-Tree Preprocessing
    (dist_dual, dist_w) ← PREPROCESS_REVERSE_TREES(G, t, Λ)
    
    // Check feasibility
    if dist_w[s] > W:
        return NoSolution
        
    // Phase 3: Initial Upper Bound
    C_UB ← +∞
    best_path ← null
    
    // Evaluate candidate paths discovered during Phase 1
    for each path P in DiscoveredPaths:
        if w(P) ≤ W and c(P) < C_UB:
            C_UB ← c(P)
            best_path ← P

    // Phase 4: Priority Queue Search
    // Priority Key: c + L_u^Λ(W - w) (admissible A* estimate)
    PQ ← MinHeap()
    
    root_lb ← EVAL_DUAL_LOWER_BOUND(s, W, Λ, dist_dual)
    PQ.push(Label(vertex=s, cost=0.0, weight=0.0, path=[s]), key=root_lb)
    
    Frontiers ← Array of ParetoFrontier[|V|]
    Frontiers[s].INSERT_AND_PRUNE(0.0, 0.0)
    
    while not PQ.isEmpty():
        curr_label ← PQ.pop()
        u ← curr_label.vertex
        c_u ← curr_label.cost
        w_u ← curr_label.weight
        
        // Target check
        if u == t:
            if c_u < C_UB:
                C_UB ← c_u
                best_path ← curr_label.path
            continue
            
        // Global Upper Bound Check
        lb_u ← EVAL_DUAL_LOWER_BOUND(u, W - w_u, Λ, dist_dual)
        if c_u + lb_u ≥ C_UB:
            continue // Pruned by Dual Hull
            
        // Edge Expansion
        for each directed edge (u, v) with cost c_e and weight w_e in G.out_edges(u):
            new_c ← c_u + c_e
            new_w ← w_u + w_e
            
            // Filter 1: Resource feasibility
            if new_w + dist_w[v] > W:
                continue // Infeasible to reach t
                
            // Filter 2: Dual Hull Bound
            rem_w ← W - new_w
            lb_v ← EVAL_DUAL_LOWER_BOUND(v, rem_w, Λ, dist_dual)
            if new_c + lb_v ≥ C_UB:
                continue // Cannot beat best known solution
                
            // Filter 3: Local Pareto Dominance
            if Frontiers[v].IS_DOMINATED(new_c, new_w):
                continue // Dominated at vertex v
                
            // Passed all filters: Update vertex frontier and enqueue
            Frontiers[v].INSERT_AND_PRUNE(new_c, new_w)
            new_path ← curr_label.path + [v]
            PQ.push(Label(vertex=v, cost=new_c, weight=new_w, path=new_path), key=new_c + lb_v)
            
    if best_path is not null:
        return Optimal(best_path, cost=C_UB, weight=w(best_path))
    else:
        return NoSolution
```
