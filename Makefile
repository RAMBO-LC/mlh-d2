PY := .venv/bin/python
export PYTHONPATH := src

.PHONY: setup test test-slow run offline-demo clean-data

setup:
	@test -x /opt/homebrew/bin/python3.12 || test "$$(python3 -c 'import sys; print(sys.version_info >= (3,11))')" = "True" || (echo "need Python 3.11+ on PATH"; exit 1)
	@test -d .venv || /opt/homebrew/bin/python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	$(PY) -c "from birdnet_analyzer.utils import ensure_model_exists; ensure_model_exists()"
	@echo "setup done. Optional (once, needs network): brew install ollama && ollama pull gemma3:4b"

test:
	$(PY) -m pytest tests/ -q

test-slow:
	$(PY) -m pytest tests/ -q -m slow

run:
	$(PY) -m fieldnotes.cli --config config.yaml web --port 8765

offline-demo:
	$(PY) scripts/offline_demo.py

clean-data:
	rm -rf data/fieldnotes.db data/clips data/journals
	@echo "local data removed (config + code untouched)."
