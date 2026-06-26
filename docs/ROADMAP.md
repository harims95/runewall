# Runewall Roadmap

## v1.0.0 (released)

- local safety runtime
- MCP stdio
- Python SDK preview
- community package verify
- 60-second demo
- PyPI publish

v1.0.0 is the stable local-first foundation. It does not include a hosted service, real signature verification, community map execution, or the full approve/execute lifecycle over MCP/SDK.

## v1.x (next)

- real signature verification
- MCP/SDK approve-execute lifecycle
- stronger agent integration examples

## Future

- hosted service
- dashboard
- remote registry
- community map execution

## Security test improvements (future)

Lower-priority improvements identified during post-v1.0.1 review.
Do not implement until the relevant feature or refactor justifies the work.

- **Patch at library level**: change `test_dry_run_no_network.py` patch targets
  from `runewall.maps.executor._httpx_get/_httpx_post` to `httpx.get`/`httpx.post`
  at the library level, matching `test_community_maps_safe_default.py`. Catches any
  code path that bypasses the executor wrapper.
- **Hypothesis fuzz tests**: add property-based tests for token redaction using
  `hypothesis.strategies.text`. Assert arbitrary generated token strings never appear
  in stdout or the action log. Catches edge cases the three hardcoded sentinels miss
  (escaped chars, truncation boundaries, base64 substrings).
- **Fix os.environ.get patch**: replace `patch("os.environ.get", return_value=None)`
  in `test_execute_with_allow_execute_true_but_no_token_does_not_call_network` with
  `patch.dict(os.environ, {...}, clear=True)`. Current approach patches globally and
  can interfere with unrelated env lookups in the same test.
- **Parameterize MCP tool coverage**: extend
  `test_mcp_dry_run_tool_does_not_call_network` to cover every tool exposed by
  `runewall mcp serve`, not only `runewall.dry_run`.
- **JSON schema pinning**: add schema assertions for public `--json` output fields
  (`executed`, `error_code`, `ok`, etc.) so field renames are caught by tests.
- **Lying manifests**: extend `test_validate_execute_enabled_map_is_rejected_without_exec`
  to also test manifests that set `execute_enabled: true` or
  `community_execution_allowed: true` explicitly; assert validator rejects them and
  does not call subprocess/httpx.
