<!-- markdownlint-disable-file -->

# Pytest Environment Isolation in Conftest

## Research questions

1. What is the canonical pytest pattern for keeping `DEPLOYMENT_TYPE` and
   `ALLOWED_REGIONS` from a developer's process environment out of unit tests?
2. Is the pytest `monkeypatch` fixture preferable to direct environment
   mutation or `unittest.mock.patch.dict` for this suite-level cleanup?
3. Will an autouse fixture in `tests/conftest.py` apply to every test under
   `tests/unit/`?
4. Why must `raising=False` be used when deleting these variables?
5. What existing terminal evidence confirms that removing the variables fixes
   the observed pollution?

## Recommendation

Add the following as `tests/conftest.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def isolate_config_environment(monkeypatch):
    monkeypatch.delenv("DEPLOYMENT_TYPE", raising=False)
    monkeypatch.delenv("ALLOWED_REGIONS", raising=False)
```

The fixture has pytest's default `function` scope, so it runs for each test
that can see it. `autouse=True` activates it without adding a fixture argument
to every test. The cleanup happens during fixture setup, before the test body
and any fixtures depending on it execute.

This protects unit tests that load configuration during test execution from
ambient shell values while retaining the original process environment after the
test. Tests that deliberately need one of these values can set it explicitly
with their own `monkeypatch.setenv(...)` call.

## Why this is the preferred pytest pattern

The official pytest monkeypatch documentation identifies `setenv` and `delenv`
as the supported mechanism for safely changing environment variables in tests.
It explicitly uses `monkeypatch.delenv("USER", raising=False)` to test the
missing-variable case and shows the same operation moved into reusable
fixtures. It also says that all monkeypatch changes are undone after the
requesting test function or fixture finishes.

That automatic, per-test restoration makes `monkeypatch` preferable here to
direct `os.environ.pop(...)`: the latter mutates process-global state and
requires handwritten restoration, including preserving whether the key existed
and what its original value was. A failed test or fixture can otherwise leave a
subsequent test with the wrong environment.

`unittest.mock.patch.dict(os.environ, ...)` can also restore a mapping when it
is used correctly as a context manager or decorator. It is not needed for this
case, though: `monkeypatch` is pytest's built-in, environment-specific API,
matches the official pytest examples, composes naturally with fixtures, and
pytest owns its teardown. No additional mocking abstraction is warranted for
two variables.

## Conftest scope and discovery

Yes. Place this fixture in `tests/conftest.py`, not in the repository root.
Pytest makes a fixture in a directory-level `conftest.py` available to tests in
that directory and its descendant directories. Therefore, a fixture in
`tests/conftest.py` is visible to all tests in `tests/unit/`. The API reference
also defines `autouse=True` as activating a fixture for all tests that can see
it.

The repository's pytest configuration sets `testpaths = ["tests/unit"]` in
`pyproject.toml`, so the proposed `tests/conftest.py` is on the parent path of
every configured test. Repository inspection found no existing root-level
`tests/conftest.py`; the only discovered `conftest.py` files are under
`.agents/skills/*/tests/`, which are unrelated to the configured unit-test
tree.

## `raising=False` is required

`monkeypatch.delenv` defaults `raising=True`. The pytest API reference states
that `delenv` raises `KeyError` when the variable does not exist unless
`raising` is `False`. These two variables are expected to be absent in a clean
developer or CI environment, so `raising=False` makes the fixture idempotent:
it deletes an ambient override when present and otherwise succeeds without
turning every test into a setup error.

## Repository evidence

* `src/shared/config.py:203` resolves `DEPLOYMENT_TYPE` at configuration
  construction.
* `src/shared/config.py:204` resolves and parses `ALLOWED_REGIONS` at
  configuration construction.
* `pyproject.toml` configures pytest with `pythonpath = ["."]` and
  `testpaths = ["tests/unit"]`.
* `tests/conftest.py` does not exist at research time. The scoped skill-test
  conftests do not provide fixtures to `tests/unit/`.

## Existing terminal evidence

The reported, already-observed Windows PowerShell validation clears the two
ambient variables and then runs the configured unit-test tree successfully:

```powershell
Remove-Item Env:DEPLOYMENT_TYPE
Remove-Item Env:ALLOWED_REGIONS
pytest tests/unit -q
```

The observed pytest exit code was `0`. This research session did not repeat the
command because the request prohibits tests that mutate the process environment.
The result supports the hypothesis that ambient values of these variables, not
the test code itself, caused the pollution.

## Sources

* Pytest documentation, "How to monkeypatch/mock modules and environments",
  retrieved 2026-07-22, current stable documentation. It documents `setenv`,
  `delenv`, automatic reversal of modifications, an autouse `conftest.py`
  fixture, and the `delenv(..., raising=False)` example:
  [https://docs.pytest.org/en/stable/how-to/monkeypatch.html](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
* Pytest API reference, "MonkeyPatch.delenv", retrieved 2026-07-22, current
  stable documentation. It specifies that `delenv` deletes a name from the
  environment and raises `KeyError` when absent unless `raising=False`:
  [https://docs.pytest.org/en/stable/reference/reference.html#pytest.MonkeyPatch.delenv](https://docs.pytest.org/en/stable/reference/reference.html#pytest.MonkeyPatch.delenv)
* Pytest documentation, "How to use fixtures", retrieved 2026-07-22, current
  stable documentation. It documents autouse fixtures and directory-level
  `conftest.py` fixture reuse and override behavior:
  [https://docs.pytest.org/en/stable/how-to/fixtures.html](https://docs.pytest.org/en/stable/how-to/fixtures.html)
* Pytest API reference, `@pytest.fixture`, retrieved 2026-07-22, current
  stable documentation. It defines `autouse=True` as activation for all tests
  that can see the fixture:
  [https://docs.pytest.org/en/stable/reference/reference.html#pytest.fixture](https://docs.pytest.org/en/stable/reference/reference.html#pytest.fixture)

## Conclusion

The canonical solution is a function-scoped autouse `monkeypatch.delenv` fixture
in `tests/conftest.py`, with `raising=False` for both variables. It isolates
each `tests/unit/` test from developer-shell configuration and lets pytest
restore the original environment automatically after each test.