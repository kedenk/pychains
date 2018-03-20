#!/usr/bin/env bash
SLEEP=0
if [[ $1 == '-' ]]
then
  echo env R=$2 P=U BFS=true python3 $D ./bin/mychains.py subjects/mathexpr.py
  env R=$2 P=U BFS=true python3 $D ./bin/mychains.py subjects/mathexpr.py
else
  start=0$1
  (for i in `seq $start 1000`; do echo $i --------; sleep $SLEEP; env BFS=true R=$i P=U python3 bin/mychains.py subjects/mathexpr.py; done ) 2>mathexpr.err | tee mathexpr.log
fi

trap times EXIT
