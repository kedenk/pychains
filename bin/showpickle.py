#!/usr/bin/env python3
import pickle
import sys
print(pickle.load(open(sys.argv[1], 'rb')))
