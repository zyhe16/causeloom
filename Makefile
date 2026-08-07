PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE := 1

VERSION := $(shell cat VERSION)
CONDITIONS := baseline,causeloom

.PHONY: test validate-skill research-matrix research-prepare package package-repo check clean

test:
	$(PYTHON) -m unittest discover -s tests -v

validate-skill:
	$(PYTHON) scripts/validate_skill.py .

research-matrix:
	mkdir -p work
	$(PYTHON) evals/scripts/generate_run_matrix.py \
		--tasks evals/research-suite.csv \
		--conditions $(CONDITIONS) \
		--repetitions 3 \
		--seed 329 \
		--output work/research-runs.csv

research-prepare: research-matrix
	$(PYTHON) evals/scripts/prepare_research_benchmark.py

package: validate-skill
	mkdir -p dist
	$(PYTHON) scripts/package_skill.py \
		--output dist/causeloom-$(VERSION).zip

package-repo: validate-skill
	mkdir -p dist
	$(PYTHON) scripts/package_repository.py \
		--output dist/causeloom-$(VERSION)-source.zip

check: validate-skill test package package-repo

clean:
	rm -rf dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
