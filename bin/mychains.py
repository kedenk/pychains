#!/usr/bin/env python3
import sys
import os
import time

sys.path.append('.')
import pychains.chain
import imp
import taintedstr
import datatypes.taintedint as taintint
import datatypes.taintedbytes as taintbytes
from inputwriter import clearDir, createDir, writeInputFile
import python_performance_measurement as perf
if __name__ == "__main__":
    arg = sys.argv[1]
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    _mod = imp.load_source('mymod', arg)
    results = []

    # create dir for files containing generated inputs
    dirName = os.path.join(*[os.getcwd(), "inputs"])
    createDir(dirName)
    for i in range(times):
        e = pychains.chain.Chain()
        (a, r) = e.exec_argument(_mod.main)
        print("Arg:", repr(a), flush=True)
        print("Eval:", repr(r), flush=True)
        taintedstr.reset_comparisons()
        taintbytes.reset_comparisons()
        taintint.reset_comparisons()

        # write generated input to file
        writeInputFile(a, dirName, "input_" + str(i) + "_" + str(time.time()))