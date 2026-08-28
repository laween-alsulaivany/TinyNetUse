# Test Suite Quality Review

Reviewed: 2026-08-27

## Scope and method

This review covered all tests in `tests/`, their corresponding production
modules in `src/tinynetuse/`, the documented behavior in `README.md` and
`DEVELOPMENT.md`, and the build and installer definitions. The goal was to
judge whether assertions demonstrate an observable contract, rather than
whether they merely mirror the current implementation.

The suite was run with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: `182 passed in 1.42s`.

## Overall assessment

The suite has a useful, professional foundation. It exercises real temporary
files for configuration behavior, real Qt widgets for dialog and IPC behavior,
and deterministic injected inputs for timing-sensitive network sampling. These
are meaningful tests that can detect regressions.

It is not a placebo suite. Most tests establish a concrete contract and would
fail after a relevant defect. The main weaknesses are concentrated in
release/installer validation and the overlay UI, where several tests use mock
collaborators or source-text matching instead of exercising the delivered
behavior.

## Findings

### P1: Normal CI does not validate an installable release artifact

`tests/test_installer.py` and the installer-related assertions in
`tests/test_startup.py` read `packaging/installer.iss` as text and check for
selected fragments. That protects against accidental removal of those exact
lines, but it cannot prove that Inno Setup accepts the script, that files are
placed in the intended destinations, that shortcuts work, or that the
uninstaller preserves/removes settings as intended.

`.github/workflows/ci.yml` runs syntax checks and pytest only. The installer is
built later in the tag-only release workflow, so a pull request can pass CI
while still breaking the installer.

Recommended action: add a Windows CI job, or a required scheduled/release
candidate job, that runs Inno Setup against a prepared folder build. At a
minimum, assert that the expected setup executable is produced. Keep the
source-text tests as focused configuration guardrails, but do not treat them as
installer acceptance tests. Continue the documented manual Windows checks for
install, upgrade, startup, and uninstall because those exercise OS-owned
behavior that unit tests cannot reliably simulate.

### P1: The central overlay display and alert presentation lack a real-widget test

`test_overlay_highlights_for_either_threshold` in `tests/test_app.py` invokes
`TinyNetUseWidget._update_speeds` with a `SimpleNamespace` and asserts the
private `_alert_active` flag. It verifies the comparison logic, but it does not
prove that a real overlay updates both labels with the correct upload/download
direction, or that the alert state changes the rendered background.

Similarly, `test_overlay_visibility_action_hides_or_restores` and
`test_reopening_graph_reuses_the_existing_window` assert calls made to mocks.
They can pass even when a real Qt widget fails to become visible, fails to raise
itself, or fails to refresh its graph.

Recommended action: construct a real `TinyNetUseWidget` with external
boundaries redirected to temporary/test doubles, then assert `dl_label.text()`,
`ul_label.text()`, visibility, graph history, and one observable alert result.
A focused offscreen render or a testable paint-state helper is appropriate for
the alert color. Keep pure threshold boundary cases as parameterized unit tests,
but pair them with this end-to-end widget check.

### P2: One test name describes a contract it does not test

`test_pyproject_uses_the_canonical_python_version` in `tests/test_version.py`
does not inspect `project["project"]["requires-python"]`. Its assertions only
verify that package version metadata is dynamically read from
`tinynetuse.version.__version__`.

This is misleading coverage: a change to the supported Python range could
break the documented Windows 11/Python 3.14.7 support policy while this test
continues to pass.

Recommended action: either rename the test to describe dynamic version
metadata, or add an explicit assertion for the required Python range. The
version metadata itself should remain a separate test because it is a valid
release contract.

### P2: Static source-text assertions are useful guardrails, not behavioral proof

Several tests in `tests/test_version.py`, `tests/test_installer.py`, and
`test_installer_shortcut_uses_the_same_entry_and_is_valid` in
`tests/test_startup.py` assert that source files contain exact strings. These
tests are not inherently invalid: they can protect release conventions that are
otherwise easy to accidentally delete. Their limitation is that a semantically
incorrect but textually matching script still passes, while a harmless refactor
can fail.

Recommended action: label and group these as build-configuration guardrails.
Where practical, test parsed configuration or generated output instead of raw
substrings. Retain a small number of exact checks for values that must remain
literal, such as the stable installer application ID.

### P2: Important network fallback and Windows API error paths are untested

`tests/test_network.py` strongly covers normal sampling, elapsed time,
counter resets, adapter disappearance, auto-route switching, and aggregate
fallback. That is a substantive set of tests.

The direct Windows route lookup test covers only the successful three-call API
sequence. It does not test unavailable DLL/entry points or nonzero return
values from `GetBestInterfaceEx`, `ConvertInterfaceIndexToLuid`, and
`ConvertInterfaceLuidToAlias`, each of which should select the documented
fallback. There is also no direct test for auto mode when no usable adapter is
available, nor for case-insensitive matching of a Windows route alias.

Recommended action: add narrow tests for each API failure boundary and for the
empty-adapter auto case. These should assert the public result (`None`, an empty
source set, or zero rates) rather than the private helper implementation.

### P2: Graph behavior is only lightly covered

`tests/test_graph_window.py` correctly verifies sample insertion, clearing, and
close notification. It does not test the user-visible behavior of applying a
new history size while retaining recent values, applying unit/color/opacity
settings, swapping colors, or opening and closing the graph through the overlay
menu.

Recommended action: add real-Qt tests for history resizing and the overlay to
graph workflow. Assertions should inspect history contents, window visibility,
and persisted configuration, not `update()` calls or painter internals.

### P3: A startup test is sensitive to the current working directory

`test_installer_shortcut_uses_the_same_entry_and_is_valid` in
`tests/test_startup.py` opens `Path("packaging/installer.iss")`, unlike
`tests/test_installer.py`, which resolves the installer from the repository
root. The former can fail when pytest is launched from a different working
directory even though the repository is correct.

Recommended action: resolve the fixture from `Path(__file__).parents[1]` or a
shared repository-root fixture. This is a test reliability issue, not an
application defect.

## Tests that are already strong

- `tests/test_config.py` uses real JSON files and validates migration, corrupt
  file preservation, invalid-value fallback, path selection, and atomic
  replacement. These assertions prove persisted behavior rather than mock
  interactions.
- `tests/test_network.py` injects snapshots and a monotonic clock, making rate
  calculation deterministic while still testing the public sampler behavior.
- `tests/test_units.py` uses boundary tables across every supported unit and
  validates conversion, formatting, automatic unit selection, and threshold
  round trips.
- `tests/test_geometry.py` covers multiple monitor layouts, partial visibility,
  malformed saved geometry, extreme coordinates, and recovery placement.
- `tests/test_settings_dialog.py` uses a real dialog, real configuration files,
  and real controls. Startup methods are appropriately mocked as an external
  Windows boundary, while configuration persistence and cancellation semantics
  are observed directly.
- `tests/test_single_instance.py` uses real Qt local IPC and Windows mutex
  behavior with unique instance IDs. This is stronger than a mocked
  single-instance test and checks the actual second-launch contract.

## Recommended priority order

1. Add a real-overlay integration test for label output, graph forwarding, and
   alert presentation.
2. Compile the installer before merge in a Windows CI or release-candidate job.
3. Correct or rename the misleading Python-version test.
4. Add network API failure and empty-source boundary tests.
5. Expand graph settings and overlay-to-graph workflow coverage.
6. Make the startup installer-file lookup independent of the working directory.

## Conclusion

The existing suite is practical and materially valuable, especially for the
core data and persistence logic. It should not be represented as complete
release or UI acceptance coverage until the P1 gaps are addressed. The tests
most likely to create false confidence are the raw installer/build string
checks and mock-driven overlay method tests; they should be supplemented, not
discarded.
