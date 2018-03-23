#!/usr/bin/env bash
if [[ $1 == '-' ]]
then
  echo "env R=$2 P=U python3 $D ./bin/mychains.py subjects/urlpy.py"
  env R=$2 P=U python3 $D ./bin/mychains.py subjects/urlpy.py
else
  start=0$1
  (for i in `seq $start 100`; do echo $i --------; env MY_RP=0.01 R=$i P=U python3 bin/mychains.py subjects/urlpy.py; done ) 2>urlpy.err | tee urlpy.log
fi

trap times EXIT
