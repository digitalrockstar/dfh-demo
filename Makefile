setup:
	pip install -r requirements.txt
	python -m dfh.seed.run

test:
	python -m pytest -q tests

run:
	uvicorn dfh.app:get_app --factory --reload --port 8000

smoke:
	python scripts/smoke.py

smoke-pos:
	python scripts/smoke_pos.py
