#!/usr/bin/env python3
import sys
sys.path.append('.')
import pychains.chain
import imp
import taintedstr
if __name__ == "__main__":
    arg = sys.argv[1]
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    _mod = imp.load_source('mymod', arg)
    results = []
    for i in range(times):
        e = pychains.chain.Chain()
        (a, r) = e.exec_argument(_mod.main)
        print("Arg:", repr(a), flush=True)
        print("Eval:", repr(r), flush=True)
        taintedstr.reset_comparisons()
