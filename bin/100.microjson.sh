start=0$1
(for i in `seq $start 1000`; do echo $i --------; sleep 1; env R=$i P=U python3 gencmd.py subjects/microjson.py; done ) 2>microjson.err | tee microjson.log
trap times EXIT
