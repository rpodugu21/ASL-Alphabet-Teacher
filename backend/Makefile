PYTHON ?= python3
BACKEND := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: all samples edge-samples severe-samples normalize normalize-edge normalize-severe clean-output

all: edge-samples severe-samples normalize normalize-edge normalize-severe

samples:
	$(PYTHON) $(BACKEND)make_edge_samples.py

edge-samples: samples

severe-samples: samples

normalize:
	$(PYTHON) $(BACKEND)run_all.py \
		--input-dir $(BACKEND)sample_sets \
		--output-dir $(BACKEND)output

normalize-edge: edge-samples
	rm -f $(BACKEND)output/edge/*.svg
	$(PYTHON) $(BACKEND)run_all.py \
		--input-dir $(BACKEND)edge_samples \
		--output-dir $(BACKEND)output/edge

normalize-severe: severe-samples
	rm -f $(BACKEND)output/severe/*.svg
	$(PYTHON) $(BACKEND)run_all.py \
		--input-dir $(BACKEND)severe_samples \
		--output-dir $(BACKEND)output/severe

clean-output:
	rm -rf $(BACKEND)output $(BACKEND)edge_samples $(BACKEND)severe_samples
