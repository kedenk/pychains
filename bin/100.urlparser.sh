(for i in `seq 0 100`; do echo $i; sleep 1; echo --------; sleep 1; env R=$i ISTRATEGY=0.1 P=C python3 gencmd.py subjects/urlparser.py; done ) 2>&1 | tee urlparser.log
