setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

test:
	.venv/bin/python -m pytest -q
	.venv/bin/python -m tests.test_scenarios

run:
	./run_all.sh
