import contextlib
import importlib.util
import io
import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)


spec = importlib.util.spec_from_file_location("candidate", sys.argv[1])
require(spec is not None and spec.loader is not None, "Cannot load module")
module = importlib.util.module_from_spec(spec)

output = io.StringIO()
with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
    spec.loader.exec_module(module)

require(output.getvalue() == "", "Import produced output")
require(callable(getattr(module, "parse_enabled", None)), "Function missing")

for value in ("true", "TRUE", " true ", "1", "yes", "\tYeS\n"):
    require(module.parse_enabled(value) is True, f"Expected True: {value!r}")

for value in ("false", "FALSE", " false ", "0", "no", "\tNo\n"):
    require(module.parse_enabled(value) is False, f"Expected False: {value!r}")

for value in ("", " ", "maybe", "2", "on", "off", "truthy"):
    try:
        module.parse_enabled(value)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected ValueError: {value!r}")

for value in (None, 0, 1, True, [], {}, b"true"):
    try:
        module.parse_enabled(value)
    except TypeError:
        pass
    else:
        raise AssertionError(f"Expected TypeError: {value!r}")

print("PASS: configured behavioral examples and silent import")