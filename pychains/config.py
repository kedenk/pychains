import os
RandomSeed = int(os.getenv('R') or '0')

MyPrefix = os.getenv('MY_PREFIX') or None

#  Maximum iterations of fixing exceptions that we try before giving up.
MaxIter = 10000

# When we get a non exception producing input, what should we do? Should
# we return immediately or try to make the input larger?
Return_Probability =  float(os.getenv('MY_RP') or '1.0')

InitiateBFS = (os.getenv('BFS') or 'false') in ['true', 'True', '1']

Debug=1

Log_Comparisons = 0

WeightedGeneration=False
