# AGENTS.md

Notes for coding agents working in this repository. `CLAUDE.md` is the design brief and holds the design
rules, `MEASURE.md` the measurement checklist and `README.md` the user documentation.

## Environment

The devcontainer in `.devcontainer/` is the supported environment. Everything the build, the tests and
the slicer need is installed by the image or created when the container is created; nothing is
installed by hand.

| Component | Location | Defined in |
|---|---|---|
| Base image `mcr.microsoft.com/devcontainers/base:3.0.10-noble`, pinned by digest | - | `.devcontainer/Dockerfile` (`FROM`) |
| Python 3.12 with the `venv` module | `/usr/bin/python3` | `Dockerfile` (`python3-venv`) |
| OpenCascade runtime libraries (`libgl1`, `libx11-6`) | system | `Dockerfile` |
| ElegooSlicer 1.5.3.5, AppImage extracted, checksum verified | `/opt/elegooslicer` (`ELEGOOSLICER_DIR`) | `Dockerfile` (`ELEGOOSLICER_VERSION`, `ELEGOOSLICER_SHA256`) |
| `elegooslicer` wrapper, runs under `xvfb-run` when `DISPLAY` is unset | `/usr/local/bin/elegooslicer` | `.devcontainer/elegooslicer` |
| Slicer host libraries (GTK 3, WebKitGTK 4.1, OpenGL, GStreamer base) | system | `Dockerfile` |
| Headless X and software OpenGL (`xvfb`, `xauth`, `libgl1-mesa-dri`) | system | `Dockerfile` |
| `shellcheck` | system | `Dockerfile` |
| Python packages, exact versions | `.venv/` | `requirements.txt`, installed by `.devcontainer/on-create.sh` |

`devcontainer.json` builds the Dockerfile and runs `on-create.sh` as its `onCreateCommand`. The script
recreates `.venv` with `--clear` every time the container is created, so the venv always matches
`requirements.txt`. It uses `onCreateCommand` because `devcontainer.vim.json` sets its own
`postCreateCommand`, which would replace one set in `devcontainer.json`.

## Checking the environment

Run these before relying on the build or the test results:

```bash
.venv/bin/python -c "import build123d, trimesh; print('python ok')"
command -v elegooslicer && test -d "${ELEGOOSLICER_DIR}/resources/profiles/Elegoo" && echo "slicer ok"
.venv/bin/python -m pytest -q -rs
```

A skip with the reason `ElegooSlicer is not installed` means the slicer is missing: the print-project
tests did not run, so do not report the suite as passing. The other skips are expected; they mark
tests that only apply to the mount style not being built.

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: libGL.so.1` when importing build123d | Container built before the Dockerfile existed, or from another image | Rebuild the container |
| `elegooslicer not found`, or `--print-dir` refused | Slicer missing from the container | Rebuild the container |
| Slicer exits with `missing host ... runtime library` | A host library is missing from the image | Add the Ubuntu package to the Dockerfile and rebuild |
| `ModuleNotFoundError` for a Python package | `.venv` out of date | Run `bash .devcontainer/on-create.sh` |

If a running container has to be fixed without a rebuild, run the same commands as the Dockerfile and
make the matching Dockerfile change in the same piece of work.

## Changing the environment

- Every system dependency goes into the Dockerfile. A package installed only in a running container is
  lost at the next rebuild.
- Python packages are pinned exactly in `requirements.txt`. To add or upgrade one, install it into a
  venv built from the current file, run the full test suite, then regenerate the pins with `pip freeze`
  and keep the header comment listing the direct dependencies up to date.
- To upgrade ElegooSlicer, read the release's Linux AppImage name and `sha256` digest from
  `https://api.github.com/repos/elegooofficial/ElegooSlicer/releases`, update `ELEGOOSLICER_VERSION` and
  `ELEGOOSLICER_SHA256` together, and check that the asset name still matches the URL pattern in the
  Dockerfile. After the rebuild, confirm that the profile names in `duct/slice.py` (`MACHINE`, `PROCESS`,
  `FILAMENT_PROFILES`) still exist under `${ELEGOOSLICER_DIR}/resources/profiles/Elegoo`, then run the
  build with `--print-dir print`, `python -m duct.slice --print-dir print` and the full test suite.
- To move the base image, update its tag and digest together and pick a release at least two weeks old.
- Shell scripts follow the Google shell style guide (`function name() {`, a `main` function, lower-case
  internal variables) and must pass `shellcheck`.

## Working on the model

```bash
source .venv/bin/activate
python -m duct.build --config configs/default.toml --coupons --print-dir print
pytest
python -m duct.slice --print-dir print
python scratch/render_views.py
```

- After any geometry change, run the build and the tests before reporting the work done.
- `out/` is generated and ignored by git. `print/` is generated too but committed: refresh it only with
  a build that has the slicer available, never by editing or copying files into it.
- `scratch/render_views.py` writes PNG renders into `scratch/` (ignored by git); it needs `xvfb-run`
  when no display is set and starts it on its own.
- Every dimension comes from `configs/default.toml` through `duct/params.py`; geometry code never
  hard-codes a value.
