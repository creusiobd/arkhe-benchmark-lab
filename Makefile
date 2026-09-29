.PHONY: test pilot eval clean all

all: test pilot eval

test:
	python -m unittest discover tests

pilot:
	python -m harness.agent_benchmark_runner --config configs/pilot.yaml

eval:
	python -m evaluator.evaluate --run results/pilot

cost:
	python -m tools.estimate_api_cost

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
