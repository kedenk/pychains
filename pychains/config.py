import os
RandomSeed = int(os.getenv('R') or '0')

MyPrefix = os.getenv('MY_PREFIX') or None

#  Maximum iterations of fixing exceptions that we try before giving up.
MaxIter = int(os.getenv('MAX_ITER') or '10000')

# When we get a non exception producing input, what should we do? Should
# we return immediately or try to make the input larger?
Return_Probability = float(os.getenv('MY_RP') or '1.00')

# The sampling distribution from which the characters are chosen.
Distribution='U'

Aggressive = True

# We can choose to load the state at some iteration if we had dumped the
# state in prior execution.
Load = 0

# Dump the state (a pickle)
Dump = False

# Where to pickle
Pickled = '.pickle/ExecFile-%s.pickle'

Track = True

Debug=1

Log_Comparisons = (os.getenv('LOG_COMPARISONS') or 'false') in ['true', 'True', '1']

WeightedGeneration=False

Comparison_Equality_Chain = 3

Dumb_Search =  (os.getenv('DUMB_SEARCH') or 'false') in ['true', 'True', '1']


Python_Specific = False #(os.getenv('PY_OPT') or 'false') in ['true', '1']
Bytecode_Specific = True

No_CTRL = (os.getenv('NOCTRL') or 'false') in ['true', '1']

Wide_Trigger = int(os.getenv('WIDE_TRIGGER') or '10')
Deep_Trigger =  int(os.getenv('DEEP_TRIGGER') or '1000')

StdErr_DevNull=(os.getenv('NO_LOG') or 'false') in {'true', '1'}
if StdErr_DevNull:
    f = open(os.devnull, 'w')
    import sys
    sys.stderr = f
