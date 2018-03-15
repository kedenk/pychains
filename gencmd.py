import pudb
import os
if os.getenv('D'): pudb.set_trace(paused=True)
import random
if os.getenv('R'): random.seed(int(os.getenv('R')))
import pychains.execfile
if os.getenv('IMAX'): pychains.execfile.MaxIter = int(os.getenv('IMAX'))
if os.getenv('CMAX'): pychains.exec_bfs.MaxIter = int(os.getenv('CMAX'))
if os.getenv('DEBUG'): pychains.execfile.Debug = int(os.getenv('DEBUG'))
if os.getenv('P'): pychains.execfile.Distribubtion = os.getenv('P')
if os.getenv('ISTRATEGY'): pychains.execfile.Return_Probability = float(os.getenv('ISTRATEGY'))
if os.getenv('TRACK'): pychains.execfile.Track = os.getenv('TRACK') == 'true'
if os.getenv('BFS'): pychains.execfile.InitiateBFS = os.getenv('BFS') == 'true'
import sys
pychains.execfile.Load = os.getenv('LOAD')
pychains.execfile.Dump = os.getenv('DUMP')
pychains.execfile.PrefixArg = os.getenv('PREFIX')
pychains.execfile.ExecFile().cmdline(sys.argv)
