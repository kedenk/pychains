#!/usr/bin/env bash
if [[ $1 == '-' ]]
then
  echo "env R=$2 P=U python3 $D ./bin/mychains.py subjects/mathexpr.py"
  env R=$2 P=U MY_RP=0.001 WIDE_TRIGGER=10000 DEEP_TRIGGER=10000 python3 $D ./bin/mychains.py subjects/py-evm-simulator/main.py
else
  start=0$1
  (for i in `seq $start 1000`; do echo $i --------; R=$2 P=U MY_RP=0.001 WIDE_TRIGGER=10000 DEEP_TRIGGER=10000 python3 $D ./bin/mychains.py subjects/py-evm-simulator/main.py; done ) 2>&1 | tee bytecodevm.log
fi

trap times EXIT