# Releasing

Use this checklist for a tagged public release.

1. Update `VERSION`, `CHANGELOG.md`, and `CITATION.cff`.
2. Refresh the frozen Causeloom evaluation snapshot:

   ```bash
   python evals/scripts/snapshot_condition.py
   ```

3. Confirm `evals/private-conditions/` is ignored and absent from the source
   archive. Private calibration policies and named results are not public
   release artifacts.
4. Regenerate benchmark charts and inspect the rendered SVGs:

   ```bash
   python docs/benchmarks/generate_charts.py
   git diff --exit-code docs/assets
   ```

5. Run the complete repository gate:

   ```bash
   make check
   ```

   Do not delete `work/` or `results/`; they may contain preserved raw benchmark
   evidence even though they are excluded from release archives.

6. Build each archive twice and compare SHA-256 hashes.
7. Confirm the source archive contains only the root `SKILL.md` plus the frozen
   public `evals/conditions/causeloom/POLICY.md` snapshot.
8. Tag the same version recorded in `VERSION` and attach:
   - the install-only skill ZIP;
   - the full source ZIP; and
   - a SHA-256 checksum file.
9. Describe benchmark evidence conservatively. Distinguish contemporaneous a5
   cells from historical a3 context and never infer blinded quality from reward,
   tokens, elapsed time, or code size.
