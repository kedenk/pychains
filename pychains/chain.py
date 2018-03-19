import pickle
import os.path
import string
import enum
import sys

import taintedstr as tainted
from taintedstr import Op, tstr
from . import config

import random
random.seed(config.RandomSeed)

All_Characters = list(string.printable)

CmpSet = [Op.EQ, Op.NE, Op.IN, Op.NOT_IN]

def log(var, i=1):
    if config.Debug >= i: print(repr(var), file=sys.stderr, flush=True)

def o(d='', var=None, i=1):
    if config.Debug >= i: print(d, repr(var) if var else '', file=sys.stdout, flush=True)

import pudb
brk = pudb.set_trace

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

def create_arg(s):
    if config.Track:
        return tainted.tstr(s)
    else:
        return s

class EState(enum.Enum):
    # A char comparison made using a previous character
    Trim = enum.auto()
    # End of string as found using tainting or a comparison with the
    # empty string
    Append = enum.auto()
    # -
    Unknown = enum.auto()

def save_trace(traces, i, file='trace'):
    if not config.Debug: return None
    with open('.t/%s-%d.txt' % (file,i), 'w+') as f:
        for i in traces: print(i, file=f)

Seen_Prefixes = set()

class Prefix:
    def __init__(self, myarg, bfs=False):
        if type(myarg) is not tainted.tstr:
            self.my_arg = create_arg(myarg)
        else:
            self.my_arg = myarg
        self.bfs = bfs

    def __repr__(self):
        return repr(self.my_arg)

    def solve(self, my_traces, i):
        raise NotImplemnted

    def create_prefix(self, myarg):
        # should be overridden in child classes
        raise NotImplemnted

    def continue_valid(self):
        return []

class DFPrefix(Prefix):

    def continue_valid(self):
        if  random.uniform(0,1) > config.Return_Probability:
            return [self.create_prefix(str(self.my_arg) + random.choice(All_Characters))]

    def create_prefix(self, myarg):
        return DFPrefix(myarg, self.bfs)

    def best_matching_str(self, elt, lst):
        largest, lelt = '', None
        for e in lst:
            common = os.path.commonprefix([elt, e])
            if len(common) > len(largest):
                largest, lelt = common, e
        return largest, lelt

    def parsing_state(self, h, arg_prefix):
        if h.op_A.x() == len(arg_prefix): return EState.Append
        elif len(h.op_A) == 1: return EState.Trim
        else: return EState.Unknown

    def comparisons_on_given_char(self, h, cmp_traces):
        return [(i,t) for i,t in enumerate(cmp_traces) if h.op_A.x() == t.op_A.x()]

    def extract_solutions(self, elt, lst_solutions, flip=False):
        fn = tainted.COMPARE_OPERATORS[elt.op]
        result = fn(str(elt.op_A), str(elt.op_B))
        if isinstance(elt.op_B, str) and len(elt.op_B) == 0:
            if Op(elt.op) in [Op.EQ, Op.NE]:
                return lst_solutions
            else:
                assert False
        else:
            myfn = fn if not flip else lambda a, b: not fn(a, b)
            if result:
                lst = [c for c in lst_solutions if myfn(str(c), str(elt.op_B))]
            else:
                lst = [c for c in lst_solutions if not myfn(str(c), str(elt.op_B))]
            return lst

    def get_lst_solutions_at_divergence(self, cmp_stack, v):
        # if we dont get a solution by inverting the last comparison, go one
        # step back and try inverting it again.
        stack_size = len(cmp_stack)
        while v < stack_size:
            # now, we need to skip everything till v
            diverge, *satisfy = cmp_stack[v:]
            lst_solutions = All_Characters
            for i,elt in reversed(satisfy):
                lst_solutions = self.extract_solutions(elt, lst_solutions, False)
            # now we need to diverge here
            i, elt = diverge
            lst_solutions = self.extract_solutions(elt, lst_solutions, True)
            if lst_solutions:
                return lst_solutions
            v += 1
        return []

    def get_corrections(self, cmp_stack, constraints):
        """
        cmp_stack contains a set of comparions, with the last comparison made
        at the top of the stack, and first at the bottom. Choose a point
        somewhere and generate a character that conforms to everything until then.
        """
        if not cmp_stack: return [l for l in All_Characters if constraints(l)]

        stack_size = len(cmp_stack)
        lst_positions = list(range(stack_size-1,-1,-1))
        solutions = []


        for point_of_divergence in lst_positions:
            lst_solutions = self.get_lst_solutions_at_divergence(cmp_stack, point_of_divergence)
            lst = [l for l in lst_solutions if constraints(l)]
            if lst:
                solutions.append(lst)
        return solutions

    def solve(self, my_traces, i):
        traces = list(reversed(my_traces))
        arg_prefix = self.my_arg
        last_char_added = arg_prefix[-1]
        # add the prefix to seen.
        Seen_Prefixes.add(str(arg_prefix))
        # we are assuming a character by character comparison.
        # so get the comparison with the last element.
        while traces:
            h, *ltrace = traces
            k = self.parsing_state(h, arg_prefix)
            log((config.RandomSeed, i, k, "is tainted", isinstance(h.op_A, tainted.tstr)), 1)
            sprefix = str(arg_prefix)

            if k == EState.Trim:
                end =  h.op_A.x()
                similar = [i for i in Seen_Prefixes if str(arg_prefix[:end]) in i
                           and len(i) > len(arg_prefix[:end])]
                fixes = [i[end] for i in similar]

                # A character comparison of the *last* char.
                # This was a character comparison. So collect all
                # comparisons made using this character. until the
                # first comparison that was made otherwise.
                # Now, try to fix the last failure
                cmp_stack = self.comparisons_on_given_char(h, traces)
                # Now, try to fix the last failure
                corr = self.get_corrections(cmp_stack, lambda i: i not in fixes)
                if not corr: raise Exception('Exhausted attempts: %s' % fixes)
                # check for line cov here.
                chars = [new_char for v in corr for new_char in v]
                chars = chars if config.WeightedGeneration else sorted(set(chars))
                new_prefix = sprefix[:-1]
                sols = [self.create_prefix("%s%s" % (new_prefix, new_char))
                        for new_char in chars]
                return sols

            elif k == EState.Append:
                # An empty comparison at the EOF
                sols = [self.create_prefix("%s%s" % (sprefix, new_char))
                        for new_char in All_Characters]

                return sols
            else:
                assert k == EState.Unknown
                # Unknown what exactly happened. Strip the last and try again
                # try again.
                traces = ltrace
                continue

        return []

class Change:
    # the class looks like
    #   change_position,
    #   position for new observation,
    #   string used for replacement,
    #   list of comparisons made on the char under observation,
    #   string that was used as input for the parent which lead to the
    #       production of this Node)
    def __init__(self, change_pos, obs_pos, rep_str, input_str):
        self.__dict__.update(locals())
        self.change_pos,self.obs_pos,self.rep_str = change_pos,obs_pos,rep_str
        self._str = (self.input_str[0:self.change_pos] + self.rep_str +
            self.input_str[self.change_pos + 1:])
        self._nxt = self._str[:self.obs_pos] + "A" + self._str[self.obs_pos:]
        self._repr = repr((self.change_pos, self.obs_pos, self.rep_str,
            self._str, self._nxt))

    # returns a new input by substituting the change position and adding a new
    # char at the next position that should be observed
    def get_next_input(self): return self._nxt
    def __str__(self): return self._str
    def __repr__(self): return self._repr

class BFSPrefix(Prefix):
    # parent is an object of class BFSPrefix
    # change is is used to determine a substitution
    #  node
    def __init__(self, prefix, fixes=[]):
        c = self.create_change_from_prefix(prefix)
        self.add_change(c)

    def add_change(self, c):
        self.change = c
        self.my_arg = c.input_str
        self.obs_pos = c.obs_pos # defines the observation position for this prefix

    def apply_change(self, c):
        self.add_change(c)
        self.my_arg = c.get_next_input()
        # defines the observation position for this prefix
        return self

    def create_change_from_prefix(self, prefix):
        last_idx = len(prefix.my_arg) - 1
        input_str = prefix.my_arg
        rep_str = prefix.my_arg[-1]
        return Change(last_idx, last_idx, rep_str, input_str)

    def create_prefix(self, my_arg, fixes=[]):
        b = BFSPrefix(self)
        b.my_arg = my_arg
        return b

    # Comparison filtering and new BFS_Prefix generation
    # lets first use a simple approach where strong equality is used for
    # replacement in the first input also we use parts of the rhs of the
    # in statement as substitution
    def solve(self, my_traces, i):
        # for now
        next_inputs = []
        only_tainted = [t for t in my_traces
              if t.opA.is_tpos_contained(self.obs_pos)]
        comparisons = [t for t in only_tainted if t.op in CmpSet]
        for t in comparisons:
            opB = [t.opB] if t.op in [Op.EQ, Op.NE] else t.opB
            next_inputs.extend(self._next_inputs(t.opA, opB))

        # add some letter as substitution as well
        # if nothing else was added, this means, that the character at the
        # position under observation did not have a comparison, so we do also
        # not add a "B", because the prefix is likely already completely wrong
        if not next_inputs: return []

        # now make the list of tuples a list of prefixes
        return [BFSPrefix(self).apply_change(c) for c in next_inputs]

    # appends a new input based on the current checking position, the subst. and
    # the value which was used for the run the next position to observe will lie
    # directly behind the substituted position
    def _new_inputs(self, pos, subst):
        return [Change(pos, pos + len(subst), subst, self.my_arg)]

    def _next_inputs(self, opA, opB):
        new_vals = [self._new_inputs(self.obs_pos, c) for c in opB]
        return sum(new_vals, []) # flatten one level

class Chain:

    def __init__(self):
        self.initiate_bfs = False
        self._my_args = []
        self.seen = set()

    def add_sys_args(self, var):
        if type(var) is not tainted.tstr:
            var = create_arg(var)
        else:
            var = create_arg(str(var))
        self._my_args.append(var)

    def sys_args(self):
        return self._my_args[-1]

    # Load the pickled state and also set the random set.
    # Used to start execution at arbitrary iterations.
    # requires prior dump
    def load(self, i):
        with open(config.Pickled % i, 'rb') as f:
            self.__dict__ = pickle.load(f)
            random.setstate(self.rstate)

    # Save the execution states at each iteration.
    def dump(self):
        with open(config.Pickled % self.start_i, 'wb') as f:
            self.rstate = random.getstate()
            pickle.dump(self.__dict__, f, pickle.HIGHEST_PROTOCOL)

    def choose_prefix(self, solutions):
        prefix = random.choice(solutions)
        return prefix

    def apply_prefix(self, prefix):
        self.current_prefix = prefix
        self.add_sys_args(prefix.my_arg)

    def log_comparisons(self):
        if config.Log_Comparisons:
            for c in tainted.Comparisons: print("%d,%s" % (c.op_A.x(), repr(c)))

    def prune(self, solutions):
        # never retry an argument.
        solutions = [s for s in solutions if repr(s.my_arg) not in self.seen]
        if self.initiate_bfs:
            return solutions
        else:
            return [random.choice(solutions)]

    def exec_argument(self, fn):
        self.start_i = 0
        if config.Load: self.load(config.Load)

        # replace interesting things
        if config.MyPrefix:
            solution_stack = [DFPrefix(config.MyPrefix)]
        else:
            solution_stack = [DFPrefix(random.choice(All_Characters))]

        for i in range(self.start_i, config.MaxIter):
            my_prefix, *solution_stack = solution_stack
            self.apply_prefix(my_prefix)
            self.start_i = i
            if config.Dump: self.dump()
            tainted.Comparisons = []
            try:
                log(">> %s" % self.sys_args(), 1)
                v = fn(self.sys_args())
                self.log_comparisons()
                o('Arg:', self.sys_args(), 0)
                solution_stack = my_prefix.continue_valid()
                if not solution_stack:
                    return v
            except Exception as e:
                self.seen.add(repr(self.current_prefix.my_arg))
                log('Exception %s' % e)
                if i == config.MaxIter//100 and config.InitiateBFS:
                    print('BFS: %s' % repr(self.current_prefix.my_arg), flush=True)
                    self.arg_at_bfs = self.current_prefix.my_arg
                    if config.Aggressive:
                        self.current_prefix = BFSPrefix(self.current_prefix)
                    else:
                        self.current_prefix.bfs = True
                    self.initiate_bfs = True
                self.traces = tainted.Comparisons
                solution_stack.extend(self.current_prefix.solve(self.traces, i))

                # prune works on the complete stack
                solution_stack = self.prune(solution_stack)

                if not solution_stack:
                    if not self.initiate_bfs:
                        # remove one character and try again.
                        new_arg = self.sys_args()[:-1]
                        if not new_arg:
                            raise Exception('DFS: No suitable continuation found')
                        solution_stack = [self.current_prefix.create_prefix(new_arg)]
                    else:
                        raise Exception('BFS: No suitable continuation found')
