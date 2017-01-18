#!/bin/bash

# Run unit tests 

source venv/bin/activate

# for test reports
pip install coverage pylint
mkdir -p pylint-results
# for Junit output
pip install pytest-cov pytest-sugar

spynl dev.test --reports
