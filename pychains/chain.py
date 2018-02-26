import pickle
import os.path
import string
import enum
import sys

import tainted
from tainted import Op, tstr

RandomSeed = int(os.getenv('R') or '0')
import random
random.seed(RandomSeed)

#  Maximum iterations of fixing exceptions that we try before giving up.
MaxIter = 10000

# When we get a non exception producing input, what should we do? Should
# we return immediately or try to make the input larger?
Return_Probability = 1.0

# The sampling distribution from which the characters are chosen.
Distribution='U'

# We can choose to load the state at some iteration if we had dumped the
# state in prior execution.
Load = 0

# Dump the state (a pickle)
Dump = False

# Where to pickle
Pickled = '.pickle/ExecFile-%s.pickle'

Track = True

InitiateBFS = True

Debug=1

Log_Comparisons = 0

WeightedGeneration=False

All_Characters = list(string.printable + string.whitespace)

CmpSet = [Op.EQ, Op.NE, Op.IN, Op.NOT_IN]

Comparison_Equality_Chain = 3

def log(var, i=1):
    if Debug >= i: print(repr(var), file=sys.stderr, flush=True)

def brk(v=True):
    if not v: return None
    import pudb
    pudb.set_trace()

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

def create_arg(s):
    if Track:
        return tainted.tstr(s, idx=0)
    else:
        return s

class EState(enum.Enum):
    # A character comparison using the last character
    Char = enum.auto()

    # A char comparison made using a previous character
    Trim = enum.auto()

    # A string token comparison
    String = enum.auto()

    # End of string as found using tainting or a comparison with the
    # empty string
    EOF = enum.auto()

    # -
    Unknown = enum.auto()

def save_trace(traces, i, file='trace'):
    if not Debug: return None
    with open('.t/%s-%d.txt' % (file,i), 'w+') as f:
        for i in traces: print(i, file=f)

class Prefix:
    def __init__(self, myarg, fixes=[]):
        if type(myarg) is not tainted.tstr:
            self.my_arg = create_arg(myarg)
        else:
            self.my_arg = myarg
        self.fixes = fixes

    def __repr__(self):
        return repr(self.my_arg)

    def solve(self, my_traces, i):
        raise NotImplemnted

    def prune(self, solutions):
        raise NotImplemnted

    def create_prefix(self, myarg, fixes=[]):
        # should be overridden in child classes
        raise NotImplemnted

    def continue_valid(self):
        return []

class DFPrefix(Prefix):

    def continue_valid(self):
        if  random.uniform(0,1) > Return_Probability:
            return [self.create_prefix(self.my_arg + random.choice(All_Characters))]

    def prune(self, solutions):
        return [random.choice(solutions)]

    def create_prefix(self, myarg, fixes=[]):
        return DFPrefix(myarg, fixes)

    def best_matching_str(self, elt, lst):
        largest, lelt = '', None
        for e in lst:
            common = os.path.commonprefix([elt, e])
            if len(common) > len(largest):
                largest, lelt = common, e
        return largest, lelt

    def parsing_state(self, h, arg_prefix):
        last_char_added = arg_prefix[-1]
        o = h.op

        if o in [Op.EQ, Op.NE] and isinstance(h.opB, str) and len(h.opB) > 1 and h.opA.x() == last_char_added.x():
            # Dont add IN and NOT_IN -- '0' in '0123456789' is a common
            # technique in char comparision to check for digits
            # A string comparison rather than a character comparison.
            return (1, EState.String, h)

        elif o in CmpSet and isinstance(h.opB, list) and max([len(opB) in h.opB]) > 1 and h.opA.x() == last_char_added.x():
            # A string comparison rather than a character comparison.
            return (1, EState.String, h)

        elif h.opA.x() == last_char_added.x():
            # A character comparison of the *last* char.
            return (1, EState.Char, h)

        elif h.opA.x() == len(arg_prefix):
            # An empty comparison at the EOF
            return (1, EState.EOF, h)

        elif len(h.opA) == 1 and h.opA.x() != last_char_added.x():
            # An early validation, where the comparison goes back to
            # one of the early chars. Imagine when we use regex /[.0-9+-]/
            # for int, and finally validate it with int(mystr)
            return (1, EState.Trim, h)

        else:
            return (-1, EState.Unknown, (h, last_char_added))

    def comparisons_on_last_char(self, h, cmp_traces):
        """
        The question we are answering is simple. What caused the last
        error, and how one may fix the error and continue.
        Fixing the last error is the absolute simplest one can go. However,
        that may not be the best especially if one wants to generate multiple
        strings. For that, we need get all the comparisons made on the last
        character -- let us call it cmp_stack. The correct way to
        generate test cases is to ensure that everything until the point
        we want to diverge is satisfied, but ignore the remaining. That is,
        choose a point i arbitrarily from cmp_stack, and get
        lst = cmp_stack[i:] (remember cmp_stack is reversed)
        and satisfy all in lst.
        """
        cmp_stack = []
        check = False
        for i, t in enumerate(cmp_traces):
            if not len(t.opA) == 1: continue
            if h.opA.x() != t.opA.x(): break
            cmp_stack.append((i, t))
        return cmp_stack

    def extract_solutions(self, elt, lst_solutions, flip=False):
        fn = tainted.COMPARE_OPERATORS[elt.op]
        result = fn(str(elt.opA), str(elt.opB))
        if isinstance(elt.opB, str) and len(elt.opB) == 0:
            if Op(elt.op) in [Op.EQ, Op.NE]:
                return lst_solutions
            else:
                assert False
        else:
            myfn = fn if not flip else lambda a, b: not fn(a, b)
            if result:
                lst = [c for c in lst_solutions if myfn(str(c), str(elt.opB))]
            else:
                lst = [c for c in lst_solutions if not myfn(str(c), str(elt.opB))]
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
                # assert elt.opA == self.last_char_added()
                lst_solutions = self.extract_solutions(elt, lst_solutions, False)
            # now we need to diverge here
            i, elt = diverge
            # assert elt.opA == self.last_char_added()
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
        fixes = self.fixes
        last_char_added = arg_prefix[-1]
        # we are assuming a character by character comparison.
        # so get the comparison with the last element.
        while traces:
            h, *ltrace = traces
            o = h.op

            idx, k, info = self.parsing_state(h, arg_prefix)
            log((RandomSeed, i, idx, k, info, "is tainted", isinstance(h.opA, tainted.tstr)), 1)

            if k == EState.Char:
                # A character comparison of the *last* char.
                # This was a character comparison. So collect all
                # comparisons made using this character. until the
                # first comparison that was made otherwise.
                # Now, try to fix the last failure
                cmp_stack = self.comparisons_on_last_char(h, traces)
                if str(h.opA) == last_char_added and o in CmpSet:
                    # Now, try to fix the last failure
                    corr = self.get_corrections(cmp_stack, lambda i: i not in fixes)
                    if not corr: raise Exception('Exhausted attempts: %s' % fixes)
                else:
                    corr = self.get_corrections(cmp_stack, lambda i: True)
                    fixes = []

                # check for line cov here.
                prefix = arg_prefix[:-1]
                sols = []
                chars = [new_char for v in corr for new_char in v]
                chars = chars if WeightedGeneration else sorted(set(chars))
                for new_char in chars:
                    arg = "%s%s" % (prefix, new_char)
                    sols.append(self.create_prefix(arg, fixes))

                return sols
            elif k == EState.Trim:
                # we need to (1) find where h.opA._idx is within
                # sys_args, and trim sys_args to that location, and
                # add a new character.
                args = arg_prefix[:h.opA.x()] + random.choice(All_Characters)
                # we already know the result for next character
                fix =  [arg_prefix[h.opA.x()]]
                sols = [self.create_prefix(args, fix)]
                return sols # VERIFY - TODO

            elif k == EState.String:
                if o in [Op.IN, Op.NOT_IN]:
                    opB = self.best_matching_str(str(h.opA), [str(i) for i in h.opB])
                elif o in [Op.EQ, Op.NE]:
                    opB = str(h.opB)
                else:
                    assert False
                common = os.path.commonprefix([str(h.opA), opB])
                assert str(h.opB)[len(common)-1] == last_char_added
                arg = "%s%s" % (arg_prefix, str(h.opB)[len(common):])
                sols = [self.create_prefix(arg)]
                return sols
            elif k == EState.EOF:
                # An empty comparison at the EOF
                sols = []
                for new_char in All_Characters:
                    arg = "%s%s" % (arg_prefix, new_char)
                    sols.append(self.create_prefix(arg))

                return sols
            elif k == EState.Unknown:
                # Unknown what exactly happened. Strip the last and try again
                # try again.
                traces = ltrace
                continue
            else:
                assert False

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
        del self.__dict__['self']
        self._str, self._repr = None, None

    # returns a new input by substituting the change position and adding a new
    # char at the next position that should be observed
    def get_next_input(self):
        next_input = str(self)
        return next_input[:self.obs_pos] + "A" + next_input[self.obs_pos:]

    def __str__(self):
        if not self._str:
            self._str = self.input_str[0:self.change_pos] + self.rep_str + self.input_str[self.change_pos + 1:]
        return self._str

    def __repr__(self):
        if not self._repr:
             self._repr = repr((self.change_pos, self.obs_pos, self.rep_str, self.input_str))
        return self._repr


class BFSPrefix(Prefix):

    already_seen = set()

    # parent is an object of class BFSPrefix
    # change is is used to determine a substitution
    #  node
    def __init__(self, prefix, fixes=[]):
        c = self.create_change_from_prefix(prefix)
        self.change = c
        self.my_arg = c.input_str
        self.obs_pos = c.obs_pos # defines the observation position for this prefix

    def apply_change(self, c):
        self.change = c
        self.obs_pos = c.obs_pos
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

    def prune(self, solutions):
        return solutions

    # Input pruning -- only current solutions which is directly applied to the
    # result of solve
    def _prune(self, solutions, traces):
        # filter for inputs, that do not lead to success, i.e. inputs that are
        # already correct and inputs that can be pruned in another form (see
        # prune_input for more information)
        for node in solutions:
            if self._prune_input(node, traces):
                solutions.remove(node)
            elif self._check_seen(node):
                solutions.remove(node)
        return solutions

    # for inputs with length greater 3 we can assume that if
    # it ends with a value which was not successful for a small input
    def _prune_input(self, node, traces):
        # we do not need to create arbitrarily long strings, such a thing will
        # likely end in an infinite string, so we prune branches starting here
        c = node.change
        if "BBBA" in c.get_next_input():
            return True
        s = str(c)
        if len(s) <= 3:
            return False
        if s[len(s) // 2:].endswith(s[0:len(s) // 2]):
            return True

        # The node is not used here? This will remove all solutions
        # from this current iteration.
        if node._comparison_chain_equal(traces):
            return True
        return False

    def _check_trace_eq(self, t1, t2):
        if len(t1) != len(t2): return False
        return not any((i,j) for (i,j) in zip(t1, t2) if t1 !=t2)

    # TODO this can be done just on the parent instead of checking for all
    # children
    def _comparison_chain_equal(self, traces):
        all_traces = [t for t in traces if type(t.opA) is tstr if t.op in CmpSet]
        initial_trace = [t for t in all_traces if t.opA.is_tpos_contained(self.obs_pos)]

        for i in range(1, Comparison_Equality_Chain):
            i_comparisons = [t for t in all_traces if t.opA.is_tpos_contained(self.obs_pos-i)]
            if not self._check_trace_eq(i_comparisons, initial_trace): return False
        return True

    # check if the input is already in the queue, if yes one can just prune it
    # at this point
    def _check_seen(self, node):
        s = node.change.get_next_input()
        if s in BFSPrefix.already_seen: return True
        BFSPrefix.already_seen.add(s)

    # Comparison filtering and new BFS_Prefix generation
    # lets first use a simple approach where strong equality is used for
    # replacement in the first input also we use parts of the rhs of the
    # in statement as substitution
    def solve(self, my_traces, i):
        # for now
        next_inputs = []
        only_tainted = [t for t in my_traces if type(t.opA) is tstr and t.opA.is_tpos_contained(self.obs_pos)]
        comparisons = [t for t in only_tainted if t.op in CmpSet]
        for t in comparisons:
            opB = [t.opB] if t.op in [Op.EQ, Op.NE] else t.opB
            next_inputs.extend(self._next_inputs(t.opA, opB))

        # add some letter as substitution as well
        # if nothing else was added, this means, that the character at the
        # position under observation did not have a comparison, so we do also
        # not add a "B", because the prefix is likely already completely wrong
        if not next_inputs: return []

        next_inputs.append((self.obs_pos, self.obs_pos + 1, "B"))
        # now make the list of tuples a list of prefixes
        return self._prune([BFSPrefix(self).apply_change(Change(obs, pos, s, self.my_arg)) for (obs, pos, s) in next_inputs], my_traces)

    # appends a new input based on the current checking position, the subst. and
    # the value which was used for the run the next position to observe will lie
    # directly behind the substituted position
    def _new_inputs(self, pos, subst):
        inputs = [(pos, pos + len(subst), subst)]
        # if the character under observation lies in the middle of the string,
        # it might be that we fulfilled the constraint and should now start with
        # appending stuff to the string again (new string will have length of
        # current plus length of the substitution minus 1 since the position
        # under observation is substituted)
        if pos < len(self.my_arg) - 1:
            inputs.append((pos, len(self.my_arg) + len(subst) - 1, subst))
        return inputs

    def _next_inputs(self, opA, opB):
        new_vals = [self._new_inputs(self.obs_pos, c) for c in opB]
        return sum(new_vals, []) # flatten one level

class Chain:

    def __init__(self):
        self.initiate_bfs = False
        self._my_args = []

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
        with open(Pickled % i, 'rb') as f:
            self.__dict__ = pickle.load(f)
            random.setstate(self.rstate)

    # Save the execution states at each iteration.
    def dump(self):
        with open(Pickled % self.start_i, 'wb') as f:
            self.rstate = random.getstate()
            pickle.dump(self.__dict__, f, pickle.HIGHEST_PROTOCOL)

    def choose_prefix(self, solutions):
        prefix = random.choice(solutions)
        return prefix

    def apply_prefix(self, prefix):
        self.current_prefix = prefix
        self.add_sys_args(prefix.my_arg)

    def log_comparisons(self):
        if Log_Comparisons:
            for c in tainted.Comparisons: print(c.opA._idx, c)

    def exec_argument(self, fn):
        self.start_i = 0
        if Load: self.load(Load)

        # replace interesting things
        solution_stack = [DFPrefix(random.choice(All_Characters))]

        for i in range(self.start_i, MaxIter):
            my_prefix, *solution_stack = solution_stack
            self.apply_prefix(my_prefix)
            self.start_i = i
            if Dump: self.dump()
            tainted.Comparisons = []
            try:
                log(">> %s" % self.sys_args(), 1)
                v = fn(self.sys_args())
                print('Arg: %s' % repr(self.sys_args()))
                self.log_comparisons()
                solution_stack = my_prefix.continue_valid()
                if not solution_stack:
                    return v
            except Exception as e:
                if i == MaxIter//100 and InitiateBFS:
                    print('with BFS', flush=True)
                    self.current_prefix = BFSPrefix(self.current_prefix)
                traces = tainted.Comparisons
                solution_stack.extend(self.current_prefix.solve(traces, i))

                # prune works on the complete stack
                solution_stack = self.current_prefix.prune(solution_stack)

                if not solution_stack:
                    if type(self.current_prefix) is not BFSPrefix:
                        # remove one character and try again.
                        new_arg = self.sys_args()[:-1]
                        if not new_arg:
                            raise Exception('No suitable continuation found')
                        solution_stack = [self.current_prefix.create_prefix(new_arg)]
                    else:
                        raise Exception('No suitable continuation found')


if __name__ == '__main__':
    import imp
    arg = sys.argv[1]
    _mod = imp.load_source('mymod', arg)
    e = Chain()
    e.exec_argument(_mod.main)
