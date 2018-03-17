start=0$1
(for i in `seq $start 100`; do echo $i; sleep 1; echo --------; sleep 1; env R=$i python3 pychains/chain.py subjects/urljava.py; done ) 2>&1 | tee url.log
