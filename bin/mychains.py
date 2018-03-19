#!/usr/bin/env python3
import sys
import pychains.chain
import imp
if __name__ == "__main__":
    arg = sys.argv[1]
    _mod = imp.load_source('mymod', arg)
    e = pychains.chain.Chain()
    e.exec_argument(_mod.main)
