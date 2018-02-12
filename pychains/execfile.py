import random
import pickle
import os.path
import string
import sys
import argparse
import logging
import bytevm.execfile as bex
from . import dataparser as dp
import enum

Min_Len = 10

MaxIter = 1000
def set_maxiter(i):
    global MaxIter
    MaxIter = i

Return_Probability = 1.0
def set_input_strategy(i):
    global Return_Probability
    Return_Probability = float(i)

Debug=0
def set_debug(i):
    global Debug
    Debug = i

Distribution='U'
def set_dist(d):
    global Distribution
    Distribution = d

def log(var, i=1):
    if Debug >= i:
        print(repr(var), file=sys.stderr, flush=True)

def d(v=True):
    if v:
        import pudb
        pudb.set_trace()

Load = os.getenv('LOAD')
Dump = os.getenv('DUMP')

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

from .vm import TrackerVM, Op
from .tstr import tstr
Pickled = '.pickle/ExecFile-%s.pickle'

def my_int(s):
    return dp.parse_int(s)

def my_float(s):
    return dp.parse_float(s)

def my_type(x):
    if '.tstr'in type(x):
        import pudb; pudb.set_trace()
        return 'str'
    return type(x)

class EState(enum.Enum):
    # Char is when we find that the last character being compared is same as
    # the last character being inserted
    Char = enum.auto()
    Trim = enum.auto()
    # Last is when the last correction goes bad.
    Last = enum.auto()
    String = enum.auto()
    EOF = enum.auto()
    Unknown = enum.auto()

All_Characters = list(string.printable + string.whitespace)

def save_trace(traces, i, file='trace'):
    if Debug > 0:
        with open('.t/%s-%d.txt' % (file,i), 'w+') as f:
            for i in traces: print(i, file=f)

class ExecFile(bex.ExecFile):
    def load(self, i):
        with open(Pickled % i, 'rb') as f:
            self.__dict__ = pickle.load(f)
            random.setstate(self.rstate)

    def dump(self):
        with open(Pickled % self.start_i, 'wb') as f:
            self.rstate = random.getstate()
            pickle.dump(self.__dict__, f, pickle.HIGHEST_PROTOCOL)

    def choose_char(self, lst):
        if Distribution=='U': return random.choice(lst)
        myarr = {i:1 for i in All_Characters}
        for i in self.my_args: myarr[i] += 1
        my_weights = [1/myarr[l] for l in lst]
        return random.choices(lst, weights=my_weights, k=1)[0]

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
        last_cmp_idx = h.opA._idx
        cmp_stack = []
        check = False
        for i, t in enumerate(cmp_traces):
            # TODO: we conflate earlier characters that match the current char.
            # This can be fixed only by tracking taint information.
            if not isinstance(t.opA, str): continue
            if not len(t.opA) == 1: continue
            if h.opA != t.opA:
                # make sure that there has not been any comparisons beyond last_cmp_idx
                check = True
            if not check:
                cmp_stack.append((i, t))
            else:
                pass
                # see microjson.py: decode_escape: ESC_MAP.get(c) why we cant always
                # transfer tstr
                #if isinstance(t.opA, str) and t.opA._idx > last_cmp_idx:
                    #assert False

        return cmp_stack

    def extract_solutions(self, elt, lst_solutions, flip=False):
        fn = TrackerVM.COMPARE_OPERATORS[elt.opnum]
        result = fn(elt.opA, elt.opB)
        if isinstance(elt.opB, str) and len(elt.opB) == 0:
            if Op(elt.opnum) in [Op.EQ, Op.NE]:
                return lst_solutions
            else:
                assert False
        else:
            myfn = fn if not flip else lambda a, b: not fn(a, b)
            if result:
                lst = [c for c in lst_solutions if myfn(c, elt.opB)]
            else:
                lst = [c for c in lst_solutions if not myfn(c, elt.opB)]
            return lst


    def get_correction(self, cmp_stack, constraints):
        """
        cmp_stack contains a set of comparions, with the last comparison made
        at the top of the stack, and first at the bottom. Choose a point
        somewhere and generate a character that conforms to everything until then.
        """
        stack_size = len(cmp_stack)
        # Can the point of divergence in execution chosen randomly from the
        # comparisions to the last character? The answer seems to be `no`
        # because there could be multiple verification steps for the current
        # last character, inverting any of which can lead us to error path.
        # DONT:

        rand = list(range(0, stack_size))

        while rand:
            # randrange is not including stack_size
            point_of_divergence = random.choice(rand)
            v = point_of_divergence

            # if we dont get a solution by inverting the last comparison, go one
            # step back and try inverting it again.
            while v < stack_size:
                # now, we need to skip everything till v
                diverge, *satisfy = cmp_stack[v:]
                lst_solutions = All_Characters
                for i,elt in reversed(satisfy):
                    assert elt.opA in [self.checked_char, self.last_fix]
                    lst_solutions = self.extract_solutions(elt, lst_solutions, False)
                # now we need to diverge here
                i, elt = diverge
                assert elt.opA in [self.checked_char, self.last_fix]
                lst_solutions = self.extract_solutions(elt, lst_solutions, True)
                if lst_solutions: break
                v += 1
            lst = [l for l in lst_solutions if constraints(l)]
            if lst: return lst
            rand.remove(point_of_divergence)
        assert False

    def kind(self, h):
        pred = TrackerVM.COMPARE_OPERATORS[h.opnum]
        cmp_result = pred(h.opA, h.opB)
        o = Op(h.opnum)

        if o in [Op.EQ, Op.NE] and isinstance(h.opB, str) and len(h.opB) > 1:
            return (1, EState.String, h)

        elif h.opA == self.checked_char:
            return (1, EState.Char, h)

        elif type(h.opA) is tstr and len(h.opA) == 1 and h.opA._idx != self.my_args[-1]._idx:
            return (1, EState.Trim, h)

        elif o in [Op.EQ, Op.IN, Op.NE, Op.NOT_IN] and h.opA == '':
            return (1, EState.EOF, h)

        elif h.opA == self.last_fix and o in [Op.IN, Op.EQ, Op.NOT_IN, Op.NE]:
            # if the comparison is eq or in and it succeeded and the character
            # compared was equal to last_fix, then this is the last match.
            return (1, EState.Last, (h, self.checked_char, self.last_fix))
        else:
            return (0, EState.Unknown, (h, self.checked_char, self.last_fix))

    def on_trace(self, i, traces, steps):
        a = self.my_args
        # we are assuming a character by character comparison.
        # so get the comparison with the last element.
        while traces:
            h, *ltrace = traces

            idx, k, info = self.kind(h)
            log((i, idx, k, info), 0)

            if hasattr(self, 'last_step') and self.last_step is not None:
                self.last_step == None
                if steps > self.last_step:
                    # our gamble paid off. So it was eof
                    pass
                else:
                    # it was not eof. Try eating the last
                    self.last_step = None
                    return self.my_args[:-1]

            if k == EState.Char:
                # my_args[-1]._idx is same as len(my_args) - 1
                assert self.my_args[-1]._idx == len(self.my_args) -1
                # This was a character comparison. So collect all
                # comparisions made using this character. until the
                # first comparison that was made otherwise.
                cmp_stack = self.comparisons_on_last_char(h, traces)
                # Now, try to fix the last failure
                self.next_opts = self.get_correction(cmp_stack, lambda i: True)
                new_char = self.choose_char(self.next_opts)
                self.next_opts = [i for i in self.next_opts if i != new_char]
                arg = "%s%s" % (self.my_args[:-1], new_char)

                self.last_fix = new_char
                self.fixes = [self.last_fix]

                self.checked_char = None
                return arg
            elif k == EState.Trim:
                # we need to (1) find where h.opA._idx is within
                # self.my_args, and trim self.my_args to that location
                args = self.my_args[h.opA._idx:]
                import pudb; pudb.set_trace()
                return args # VERIFY - TODO

            elif k == EState.String:
                #assert h.opA == self.last_fix or h.opA == self.checked_char
                common = os.path.commonprefix(h.oargs)
                if self.checked_char:
                    # if checked_char is present, it means we passed through
                    # EState.EOF
                    assert h.opB[len(common)-1] == self.checked_char
                    arg = "%s%s" % (self.my_args, h.opB[len(common):])
                elif self.last_fix:
                    assert h.opB[len(common)-1] == self.last_fix
                    arg = "%s%s" % (self.my_args, h.opB[len(common):])

                self.last_fix = None
                self.checked_char = None
                return arg
            elif k == EState.EOF:
                new_char = self.choose_char(All_Characters)
                arg = "%s%s" % (self.my_args, new_char)

                self.checked_char = new_char
                self.last_fix = None
                return arg
            elif k == EState.Last:
                # This was a character comparison. So collect all
                # comparisions made using this character. until the
                # first comparison that was made otherwise.
                cmp_stack = self.comparisons_on_last_char(h, traces)
                # Now, try to fix the last failure
                self.next_opts = self.get_correction(cmp_stack, lambda i: i not in self.fixes and i != self.checked_char)
                if not self.next_opts:
                    raise Exception('Exhausted attempts: %s' % self.fixes)
                new_char = self.choose_char(self.next_opts)
                arg = "%s%s" % (self.my_args[:-1], new_char)

                self.last_fix = new_char
                self.fixes.append(self.last_fix)

                self.checked_char = None
                return arg
            else:
                # probably a late validation. trim the last and
                # try again.
                traces = ltrace
                continue

                # it is possible that we are seeing an EOF. To check, try
                # inserting a value
                #new_char = self.choose_char(All_Characters)
                #arg = "%s%s" % (self.my_args, new_char)
                #self.last_step = steps

                #self.checked_char = new_char
                #self.last_fix = None
                #return arg
            assert False

    def exec_code_object(self, code, env):
        self.start_i = 0
        if Load:
            self.load(Load)
            sys.argv[1] = self.my_args
        else:
            self.my_args = sys.argv[1]
            self.last_fix = self.my_args[-2] if len(self.my_args) > 1 else None
            # The last_character assignment made is the first character assigned
            # when starting.
            self.checked_char = self.my_args[-1]

        # replace interesting things
        # env['type'] = my_type
        env['int'] = my_int
        env['float'] = my_float

        for i in range(self.start_i, MaxIter):
            self.start_i = i
            if Dump: self.dump()
            vm = TrackerVM()
            try:
                log(">> %s" % self.my_args, 0)
                v = vm.run_code(code, f_globals=env)
                print('Arg: %s' % repr(self.my_args))
                if random.uniform(0,1) > Return_Probability: # and len(self.my_args) < Min_Len
                    self.checked_char = self.choose_char(All_Characters)
                    self.my_args = tstr("%s%s" % (sys.argv[1], self.checked_char), idx=0)
                    sys.argv[1] = self.my_args
                else:
                    return v
            except Exception as e:
                traces = list(reversed(vm.get_trace()))
                save_trace(traces, i)
                save_trace(vm.byte_trace, i, file='byte')
                self.my_args = tstr(self.on_trace(i, traces, vm.steps), idx=0)
                sys.argv[1] = self.my_args

    def cmdline(self, argv):
        parser = argparse.ArgumentParser(
            prog="bytevm",
            description="Run Python programs with a Python bytecode interpreter.",
        )
        parser.add_argument(
            '-m', dest='module', action='store_true',
            help="prog is a module name, not a file name.",
        )
        parser.add_argument(
            '-v', '--verbose', dest='verbose', action='store_true',
            help="trace the execution of the bytecode.",
        )
        parser.add_argument(
            'prog',
            help="The program to run.",
        )
        parser.add_argument(
            'args', nargs=argparse.REMAINDER,
            help="Arguments to pass to the program.",
        )
        args = parser.parse_args()

        level = logging.DEBUG if args.verbose else logging.WARNING
        logging.basicConfig(level=level)

        self.my_args = []
        self.checked_char = self.choose_char(All_Characters)
        new_argv = [args.prog] + [tstr(self.checked_char, idx=0)]
        if args.module:
            self.run_python_module(args.prog, new_argv)
        else:
            self.run_python_file(args.prog, new_argv)
