# Offline command regression tests

Run from the repository root with Python 3.11 or newer:

```sh
python -m unittest discover -s tests -v
```

The tests import the production parameter, command and device modules with
minimal Home Assistant stubs. They extract the actual service parameter parser
and HTTP payload builder from their source functions to avoid importing account
setup dependencies. HTTP requests use an in-memory session; these tests do not
start Home Assistant or send appliance commands.

`fixtures/universal_request.json` contains command parameters from a failing
Haier XF 6B2M3PX `iot_voice_universal` request. Device and account identifiers
are excluded. The option ranges come from the device's program details:
`diverterLevel` accepts 0/1/2/6, the five binary options accept 0/1, and
`waterHard` accepts 0 through 7. The separate synthetic `eco` fixture deliberately
uses a smaller range to check that values valid for settings cannot bypass a
program's own validation.

The payload assertions cover the complete Universal parameters and ancillary
parameters, the full API program identifier, optional `prStr`, and API rejection.
Washer tests retain the `PROGRAMS.WM_WD` identifier and the legacy direct-send
fallback introduced by upstream PR #332.

To reproduce failures against an unmodified checkout, set `HON_FIX_SOURCE` to
its root directory before running these tests.
