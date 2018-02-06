import pudb
import os
if os.getenv('D'): pudb.set_trace(paused=False)
import random
if os.getenv('R'): random.seed(int(os.getenv('R')))
mi = int(os.getenv('I')) if os.getenv('I') else 100000
import pygen.execfile
pygen.execfile.set_maxiter(mi)
import sys
pygen.execfile.ExecFile().cmdline(sys.argv)
