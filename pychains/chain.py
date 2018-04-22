import os.path
import string
import enum
import sys

import taintedstr as tainted
from taintedstr import Op, tstr
from . import config

import random
random.seed(config.RandomSeed)

All_Characters = list(string.ascii_letters + string.digits + string.punctuation) \
        if config.No_CTRL else list(string.printable)

CmpSet = [Op.EQ, Op.NE, Op.IN, Op.NOT_IN]

def log(var, i=1):
    if config.Debug >= i: print(repr(var), file=sys.stderr, flush=True)

def o(d='', var=None, i=1):
    if config.Debug >= i:
        print(d, repr(var) if var else '', file=sys.stdout, flush=True)

import pudb
brk = pudb.set_trace

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

def create_arg(s):
    return tainted.tstr(s)

class EState(enum.Enum):
    # A char comparison made using a previous character
    Trim = enum.auto()
    # End of string as found using tainting or a comparison with the
    # empty string
    Append = enum.auto()
    # -
    Unknown = enum.auto()

    # Python Specific
    Char = enum.auto()

    # A string token comparison
    String = enum.auto()

    # End of string as found using tainting or a comparison with the
    # empty string
    EOF = enum.auto()

class Prefix:
    def __init__(self, myarg):
        self.my_arg = tainted.tstr(str(myarg))

    def __repr__(self):
        return repr(self.my_arg)

    def solve(self, my_traces, i, seen):
        raise NotImplemnted

    def create_prefix(self, myarg):
        # should be overridden in child classes
        raise NotImplemnted

    def continue_valid(self):
        return []

class Search(Prefix):

    def continue_valid(self):
        if  random.uniform(0,1) > config.Return_Probability:
            return [self.create_prefix(str(self.my_arg) +
                random.choice(All_Characters))]

    def parsing_state(self, h, arg_prefix):
        assert h.op_A.x() <= len(arg_prefix)
        if h.op_A.x() == len(arg_prefix): return EState.Append
        elif len(h.op_A) == 1 and h.op_A.x() == arg_prefix[-1].x(): return EState.Trim
        elif len(h.op_A) == 0: return EState.Trim
        else: return EState.Unknown

    def predicate_compare(self, t1, tx):
        # should be only Op.EQ
        if t1.op in [Op.IN]:
            x = t1.op_A in t1.op_B
            y = tx.op_A in tx.op_B
            return x == y and t1.op_B == tx.op_B
        elif t1.op in [Op.EQ, Op.NE]:
            x = t1.op_A == t1.op_B
            y = tx.op_A == tx.op_B
            return x == y and t1.op_B == tx.op_B
        assert False

    def comparisons_at(self, x, cmp_traces):
        # we need to get all comparisons that involve x index
        return [t for t in cmp_traces if x in t.op_A._taint]

    def get_previous_fixes(self, h, sprefix, seen):
        end = h.op_A.x()
        similar = [i for i in seen if sprefix[:end] in i and
                   len(i) > len(sprefix[:end])]
        return [i[end] for i in similar]

    def get_comparison_len(self, traces):
        # how many of the last characters added had same comparisons?
        arg_prefix = self.my_arg
        sols = []
        while traces:
            h, *ltrace = traces
            # if this fails we have to consider
            # expanding h.op_A also.
            assert len(h.op_A._taint) <= 1
            k = self.parsing_state(h, arg_prefix)
            if k == EState.Append or EState.EOF:
                at_idx0 = arg_prefix[-1].x()
                cmp0_ = self.comparisons_at(at_idx0, traces)
                cmp0 = sum([i.expand() for i in cmp0_ if i.op_A.x() == at_idx0], [])
                end = h.op_A.x()-2
                for i in range(end, 0, -1):
                    at_idxi = arg_prefix[i].x()
                    cmpi_ = self.comparisons_at(arg_prefix[i].x(), traces)
                    cmpi = sum([i.expand() for i in cmpi_ if i.op_A.x() == at_idxi], [])
                    if len(cmp0) != len(cmpi): return end - i
                    for p1, p2 in zip(cmp0, cmpi):
                        if not self.predicate_compare(p1, p2):
                            return end - i
                return end
            elif k == EState.Trim:
                return 1
            elif k == EState.Unknown:
                traces = ltrace
                continue
            else:
                assert False
        return -1

COMPARE_OPERATORS = {
        Op.EQ: lambda x, y: x == y,
        Op.NE: lambda x, y: x != y,
        Op.IN: lambda x, y: x in y,
}

def get_op(o):
    v = COMPARE_OPERATORS[o]
    if not v:
        print('No def for ', o, file=sys.stderr)
        assert False
    return v


class DeepSearch(Search):

    def create_prefix(self, myarg): return DeepSearch(myarg)

    def extract_solutions(self, lelt, lst_solutions, at_idx, flip=False):
        comparisons = [i for i in lelt.expand() if i.op_A.x() == at_idx]
        if not comparisons: return lst_solutions
        solutions = set()
        for elt in comparisons:
            fn = get_op(elt.op)
            result = elt.r
            if isinstance(elt.op_B, str) and len(elt.op_B) == 0:
                assert elt.op in [Op.EQ]
                solutions.update(lst_solutions)
            else:
                myfn = fn if not flip else lambda a, b: not fn(a, b)
                fres = lambda x: x if result else not x
                lst = {c for c in lst_solutions if fres(myfn(str(c), str(elt.op_B)))}
                solutions.update(lst)
        return solutions

    def get_lst_solutions_at_divergence(self, cmp_stack, v, at_idx):
        # if we dont get a solution by inverting the last comparison, go one
        # step back and try inverting it again.
        stack_size = len(cmp_stack)
        while v < stack_size:
            # now, we need to skip everything till v
            diverge, *satisfy = cmp_stack[v:]
            lst_solutions = All_Characters
            for elt in reversed(satisfy):
                lst_solutions = self.extract_solutions(elt, lst_solutions, at_idx, False)
            # now we need to diverge here
            elt = diverge
            lst_solutions = self.extract_solutions(elt, lst_solutions, at_idx, True)
            if lst_solutions:
                return lst_solutions
            v += 1
        return []

    def get_corrections(self, cmp_stack, constraints, at_idx):
        """
        cmp_stack contains a set of comparions, with the last comparison made
        at the top of the stack, and first at the bottom. Choose a point
        somewhere and generate a character that conforms to everything until
        then.
        """
        if not cmp_stack or config.Dumb_Search:
            return [[l] for l in All_Characters if constraints(l)]

        stack_size = len(cmp_stack)
        lst_positions = list(range(stack_size-1,-1,-1))
        solutions = []

        for point_of_divergence in lst_positions:
            lst_solutions = self.get_lst_solutions_at_divergence(cmp_stack, point_of_divergence, at_idx)
            lst = [l for l in lst_solutions if constraints(l)]
            if lst:
                solutions.append(lst)
        return solutions

    def solve(self, traces, i, seen):
        arg_prefix = self.my_arg
        sprefix = str(arg_prefix)
        # add the prefix to seen.
        # we are assuming a character by character comparison.
        # so get the comparison with the last element.
        while traces:
            h, *ltrace = traces
            # if this fails we have to consider
            # expanding h
            assert len(h.op_A._taint) <= 1
            k = self.parsing_state(h, arg_prefix)
            log((config.RandomSeed, i, k, "is tainted", isinstance(h.op_A, tainted.tstr)), 1)
            end =  h.op_A.x()
            new_prefix = sprefix[:end]
            fixes = self.get_previous_fixes(h, sprefix, seen)

            if k == EState.Trim:
                # A character comparison of the *last* char.
                # This was a character comparison. So collect all
                # comparisons made using this character. until the
                # first comparison that was made otherwise.
                # Now, try to fix the last failure
                cmp_stack = self.comparisons_at(end, traces)
                # Now, try to fix the last failure
                corr = self.get_corrections(cmp_stack, lambda i: i not in fixes, end)
                if not corr: raise Exception('Exhausted attempts: %s' % fixes)
                # check for line cov here.
                chars = sorted(set(sum(corr, [])))

            elif k == EState.Append:
                assert new_prefix == sprefix
                #assert len(fixes) == 0
                # An empty comparison at the EOF
                chars = All_Characters
            else:
                assert k == EState.Unknown
                # Unknown what exactly happened. Strip the last and try again
                # try again.
                traces = ltrace
                continue

            return [self.create_prefix("%s%s" % (new_prefix, new_char))
                    for new_char in chars]

        return []

class WideSearch(Search):

    def create_prefix(self, myarg): return WideSearch(myarg)

    def comparison_chain_equal(self, traces):
        arg = self.my_arg
        cmp_stack1 = self.comparisons_at(arg[-1].x(), traces)
        for i_eq in range(config.Comparison_Equality_Chain):
            cmp_stackx = self.comparisons_at(arg[-(i_eq+2)].x(), traces)

            if len(cmp_stack1) != len(cmp_stackx): return False
            for i,t1 in enumerate(cmp_stack1):
                tx = cmp_stackx[i]
                if str(t1.op) != str(tx.op):
                    return False
                if not self.predicate_compare(t1, tx):
                    return False
        return True



    def solve(self, traces, i, seen):
        # Fast predictive solutions. Use only known characters to fill in when
        # possible.

        arg_prefix = self.my_arg
        sols = []
        while traces:
            h, *ltrace = traces
            end = h.op_A.x()
            k = self.parsing_state(h, arg_prefix)
            log((config.RandomSeed, i, k, "is tainted",
                isinstance(h.op_A, tainted.tstr)), 1)
            sprefix = str(arg_prefix)
            fixes = self.get_previous_fixes(h, sprefix, seen)

            cmp_stack = self.comparisons_at(end, traces)
            tainted_cmp = sum([[j for j in t.expand() if j.op_A.x() == end]
                for t in cmp_stack], [])
            opBs = [[t.opB] if t.op in [Op.EQ, Op.NE] else t.opB
                    for t in tainted_cmp]
            corr = [i for i in sum(opBs, []) if i and i not in fixes]

            if k == EState.Trim:
                if not corr:
                    return sols
            elif k == EState.Append:
                if not corr:
                    # last resort. Use random fill in
                    sols.append(self.create_prefix("%s%s" %
                        (sprefix,random.choice(All_Characters))))
                    traces = [i for i in traces if len(i.opA) > 0] # ignore '' eq ''
                    continue

            chars = corr if config.WeightedGeneration else sorted(set(corr))
            new_prefix = sprefix[:end]
            for new_char in chars:
                sols.append(self.create_prefix("%s%s" % (new_prefix, new_char)))
            return sols

        return []

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
            if hasattr(self.current_prefix, 'first'):
                return  solutions
            else:
                return  solutions
                # return  [s for s in solutions if not s.comparison_chain_equal(self.traces)]
        else:
            return [random.choice(solutions)]

    def exec_argument(self, fn):
        self.start_i = 0
        # replace interesting things
        arg = config.MyPrefix if config.MyPrefix else random.choice(All_Characters)
        solution_stack = [DeepSearch(arg)] # start deep

        for i in range(self.start_i, config.MaxIter):
            my_prefix, *solution_stack = solution_stack
            self.apply_prefix(my_prefix)
            self.start_i = i
            try:
                log(">> %s" % self.sys_args(), 1)
                v = fn(self.sys_args())
                self.log_comparisons()
                solution_stack = my_prefix.continue_valid()
                if not solution_stack:
                    return (self.sys_args(), v)
            except Exception as e:
                self.seen.add(str(self.current_prefix.my_arg))
                log('Exception %s' % e)
                self.traces = list(reversed(self.sys_args().comparisons))
                sim_len = self.current_prefix.get_comparison_len(self.traces)
                self.current_prefix.sim_length = sim_len
                if not self.initiate_bfs and sim_len > config.Wide_Trigger or len(self.sys_args()) % config.Wide_Trigger == 0:
                    print('Wide: %s' % repr(self.current_prefix.my_arg), flush=True, file=sys.stderr)
                    self.arg_at_bfs = self.current_prefix.my_arg
                    self.current_prefix = WideSearch(str(self.current_prefix.my_arg))
                    self.current_prefix.first = True
                    self.initiate_bfs = True
                elif self.initiate_bfs and len(solution_stack) > config.Deep_Trigger:
                    # choose the most promising - TODO
                    print('Deep: %s' % repr(self.current_prefix.my_arg), flush=True, file=sys.stderr)
                    self.current_prefix = DeepSearch(str(self.current_prefix.my_arg))
                    self.initiate_bfs = False

                new_solutions = self.current_prefix.solve(self.traces, i, self.seen)
                if self.initiate_bfs:
                    solution_stack = solution_stack + self.prune(new_solutions)
                else:
                    my_len = float('Inf')
                    choice = self.prune(new_solutions)
                    for i in choice + solution_stack:
                        sim_len = i.sim_length if hasattr(i, 'sim_length') else float('Inf')
                        if sim_len < my_len:
                            my_len = sim_len
                            choice = [i]
                    solution_stack = choice

                if not solution_stack:
                    if not self.initiate_bfs:
                        # remove one character and try again.
                        new_arg = self.sys_args()[:-1]
                        if not new_arg:
                            raise Exception('DFS: No suitable continuation found')
                        solution_stack = [self.current_prefix.create_prefix(new_arg)]
                    else:
                        raise Exception('BFS: No suitable continuation found')
