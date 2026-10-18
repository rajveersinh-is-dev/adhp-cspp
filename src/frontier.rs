//! Strict Pareto frontier representation for bicriteria label setting.
//!
//! Provides mathematically exact non-dominated Pareto frontier operations without
//! artificial tolerance inflation that could falsely discard non-dominated trade-offs.

/// A point on the bicriteria (cost, weight) Pareto frontier.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ParetoPoint {
    /// Objective traversal cost.
    pub cost: f64,
    /// Resource consumption weight.
    pub weight: f64,
}

/// A non-dominated Pareto frontier at a vertex, maintained sorted by weight ascending.
///
/// In any valid Pareto frontier sorted by weight ascending:
/// $$w_1 < w_2 < \dots < w_k \implies c_1 > c_2 > \dots > c_k$$
///
/// A candidate label $(c, w)$ is weakly dominated by point $p$ if:
/// $$w_p \le w \quad \land \quad c_p \le c$$
#[derive(Clone, Default, Debug, PartialEq)]
pub struct VertexFrontier {
    points: Vec<ParetoPoint>,
}

impl VertexFrontier {
    /// Creates an empty vertex frontier.
    pub fn new() -> Self {
        Self { points: Vec::new() }
    }

    /// Returns the number of non-dominated points in the frontier.
    #[inline(always)]
    pub fn len(&self) -> usize {
        self.points.len()
    }

    /// Returns true if the frontier contains no points.
    #[inline(always)]
    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }

    /// Clears all points from the frontier.
    #[inline(always)]
    pub fn clear(&mut self) {
        self.points.clear();
    }

    /// Returns all non-dominated points in the frontier.
    #[inline(always)]
    pub fn points(&self) -> &[ParetoPoint] {
        &self.points
    }

    /// Checks if a candidate label `(new_c, new_w)` is weakly dominated by any existing point.
    ///
    /// Mathematical definition: Point $p$ weakly dominates candidate $q$ if:
    /// $$c_p \le c_q \quad \land \quad w_p \le w_q$$
    ///
    /// Because `points` is sorted by weight ascending and costs are strictly decreasing,
    /// among all points with $w_p \le new\_w$, the point with the largest weight $\le new\_w$
    /// has the minimum cost. Thus, we binary search in $O(\log |F|)$ time for the last point
    /// with weight $\le new\_w$ and check its cost.
    #[inline(always)]
    pub fn is_dominated(&self, new_c: f64, new_w: f64) -> bool {
        if self.points.is_empty() {
            return false;
        }
        let pos = self.points.partition_point(|pt| pt.weight <= new_w);
        if pos > 0 {
            return self.points[pos - 1].cost <= new_c;
        }
        false
    }

    /// Prunes any existing points in the frontier that are weakly dominated by `(new_c, new_w)`
    /// and inserts the new non-dominated point in sorted order.
    #[inline(always)]
    pub fn insert_and_prune(&mut self, new_c: f64, new_w: f64) {
        // Remove existing points weakly dominated by the new point:
        // pt is dominated by new if new_c <= pt.cost && new_w <= pt.weight
        self.points
            .retain(|pt| !(new_c <= pt.cost && new_w <= pt.weight));

        // Binary search insertion position maintaining sorted order by weight ascending
        let pos = self.points.partition_point(|pt| pt.weight < new_w);

        self.points.insert(
            pos,
            ParetoPoint {
                cost: new_c,
                weight: new_w,
            },
        );
    }
}
