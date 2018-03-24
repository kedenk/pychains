#!/usr/bin/env bash
SLEEP=0
if [[ $1 == '-' ]]
then
  echo env R=$2 P=U python3 $D ./bin/mychains.py subjects/urljava.py
  env R=$2 P=U python3 $D ./bin/mychains.py subjects/urljava.py
else
  start=0$1
  (for i in `seq $start 100`; do echo $i --------; sleep $SLEEP; env MY_RP=0.01 R=$i P=U python3 bin/mychains.py subjects/urljava.py; done ) 2>urljava.err | tee urljava.log
fi

trap times EXIT
