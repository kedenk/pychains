import pudb
import os
if os.getenv('D'): pudb.set_trace(paused=True)
import random
if os.getenv('R'): random.seed(int(os.getenv('R')))
mi = int(os.getenv('I')) if os.getenv('I') else 100000
import pygen.execfile
pygen.execfile.set_maxiter(mi)
if os.getenv('D'): pygen.execfile.set_debug(int(os.getenv('D')))
import sys
pygen.execfile.ExecFile().cmdline(sys.argv)
