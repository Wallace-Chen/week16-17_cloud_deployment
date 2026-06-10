.PHONY: train test

train:
	python3 scripts/train_baseline_model.py

test:
	python3 -m unittest discover -s tests -v
