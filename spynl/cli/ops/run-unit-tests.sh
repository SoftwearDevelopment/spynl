#!/bin/bash

# Run unit tests 

source venv/bin/activate

# for test reports
pip install coverage pylint
mkdir -p pylint-results
# for Junit output
pip install pytest-cov pytest-sugar

cd spynl
py.test --junit-xml=pytests.xml --cov spynl --cov-report xml --cov-append
cd ..

spynl dev.test --reports
