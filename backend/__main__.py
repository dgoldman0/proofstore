"""Entry point for running the proofstore CLI via `python -m proofstore`."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())