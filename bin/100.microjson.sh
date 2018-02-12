#(for i in `seq 1 100`; do echo $i; echo --------; sleep 1; env R=$i P=C python3 gencmd.py subjects/microjson.py; done ) 2>microjson.err | tee microjson.log
(for i in `seq 1 100`; do echo $i --------; sleep 1; env R=$i P=U python3 gencmd.py subjects/microjson.py; done ) 2>microjson.err | tee microjson.log
