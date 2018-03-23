#!/usr/bin/env bash
if [[ $1 == '-' ]]
then
  echo env R=$2 P=U python3 $D bin/mychains.py subjects/microjson.py
  env R=$2 P=U python3 $D bin/mychains.py subjects/microjson.py
else
  start=0$1
  (for i in `seq $start 100`; do echo $i --------; sleep 1; env R=$i P=U python3 bin/mychains.py subjects/microjson.py; done ) 2>microjson.err | tee microjson.log
fi

trap times EXIT
