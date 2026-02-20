#!/usr/bin/env bash
set -e

source venv/bin/activate
uvicorn main:app --reload
