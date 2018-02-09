import pudb
import os
if os.getenv('D'): pudb.set_trace(paused=True)
import random
if os.getenv('R'): random.seed(int(os.getenv('R')))
mi = int(os.getenv('I')) if os.getenv('I') else 10000
import pychains.execfile
pychains.execfile.set_maxiter(mi)
if os.getenv('D'): pychains.execfile.set_debug(int(os.getenv('D')))
if os.getenv('P'): pychains.execfile.set_dist(os.getenv('P'))
if os.getenv('LARGE'): pychains.execfile.set_input_strategy(os.getenv('LARGE'))
import sys
pychains.execfile.ExecFile().cmdline(sys.argv)
