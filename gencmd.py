import pudb
import os
if os.getenv('D'): pudb.set_trace(paused=True)
import random
if os.getenv('R'): random.seed(int(os.getenv('R')))
mi = int(os.getenv('I')) if os.getenv('I') else 100000
import pygen.execfile
pygen.execfile.set_maxiter(mi)
if os.getenv('D'): pygen.execfile.set_debug(int(os.getenv('D')))
if os.getenv('P'): pygen.execfile.set_dist(os.getenv('P'))
if os.getenv('LARGE'): pygen.execfile.set_input_strategy(os.getenv('LARGE'))
import sys
pygen.execfile.ExecFile().cmdline(sys.argv)
