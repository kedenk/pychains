#!/usr/bin/env bash

echo "env R=$1 P=U python3 $D ./bin/mychains.py subjects/mathexpr.py $2"
env R=$1 P=U MY_RP=0.01 PY_OPT=1 WIDE_TRIGGER=10000 DEEP_TRIGGER=10000 python3 $D ./bin/mychains.py subjects/py-evm-simulator/main.py $2

trap times EXIT