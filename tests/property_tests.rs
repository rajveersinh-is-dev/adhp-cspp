//! Formal property-based tests verifying mathematical invariants of ADHP.

use adhp_cspp::dijkstra::dijkstra_backward;
use adhp_cspp::instance_generator::generate_anticorrelated_instance;

#[test]
fn test_dual_envelope_monotonicity_and_convexity() {
    let inst = generate_anticorrelated_instance(30, 0.25, 0.5, 42);
    let t = inst.target;
    let lambdas = vec![0.0, 0.5, 1.2, 2.5, 5.0];

    let mut dist_dual = Vec::new();
    for &l in &lambdas {
        dist_dual.push(dijkstra_backward(&inst.graph, t, l, false));
    }

    let eval_bound = |u: usize, delta_w: f64| -> f64 {
        let mut max_val = f64::NEG_INFINITY;
        for (k, &l) in lambdas.iter().enumerate() {
            let v = dist_dual[k][u] - l * delta_w;
            if v > max_val {
                max_val = v;
            }
        }
        max_val
    };

    // Verify for every vertex in the graph
    for (u, &d_0) in dist_dual[0].iter().enumerate() {
        if d_0.is_infinite() {
            continue;
        }

        // 1. Monotonicity Test: delta_w1 < delta_w2 => L(delta_w1) >= L(delta_w2)
        let mut prev_bound = eval_bound(u, 0.0);
        for step in 1..=100 {
            let w = (step as f64) * 5.0;
            let curr_bound = eval_bound(u, w);
            assert!(
                curr_bound <= prev_bound + 1e-9,
                "Monotonicity violation at vertex {}: L({}) = {} > L(prev) = {}",
                u,
                w,
                curr_bound,
                prev_bound
            );
            prev_bound = curr_bound;
        }

        // 2. Convexity Test: L(0.5 * w1 + 0.5 * w2) <= 0.5 * L(w1) + 0.5 * L(w2)
        for w1 in [10.0, 30.0, 50.0] {
            for w2 in [40.0, 70.0, 100.0] {
                let mid_w = 0.5 * (w1 + w2);
                let l_mid = eval_bound(u, mid_w);
                let l_avg = 0.5 * (eval_bound(u, w1) + eval_bound(u, w2));

                assert!(
                    l_mid <= l_avg + 1e-9,
                    "Convexity violation at vertex {}: L(mid) = {} > avg = {}",
                    u,
                    l_mid,
                    l_avg
                );
            }
        }

        // 3. Dominance over 1D Cost Bound: L(w) >= d_c(u, t)
        let d_c = dist_dual[0][u];
        for w in [5.0, 20.0, 50.0, 150.0] {
            let lb = eval_bound(u, w);
            assert!(
                lb >= d_c - 1e-9,
                "Dominance violation at vertex {}: L({}) = {} < d_c = {}",
                u,
                w,
                lb,
                d_c
            );
        }
    }
}
