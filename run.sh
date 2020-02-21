#!/bin/bash
pipenv install --skip-lock 
pipenv run ./parse_berlinale.py berlinale2020.json
