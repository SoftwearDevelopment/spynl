#!/bin/bash

# Run unit tests 

source venv/bin/activate

# for test reports
pip install coverage pylint
mkdir -p pylint-results
# for Junit output
pip install pytest-cov pytest-sugar

py.test spynl/tests --junit-xml=pytests.xml --cov spynl --cov-report xml --cov-append

spynl dev.test --reports
