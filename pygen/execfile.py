import random
import dis
import os.path
import string
import sys
import argparse
import logging
import bytevm.execfile as bex
import bytevm.pyvm2 as pvm
import enum

MaxIter = 1000
def set_maxiter(i):
    global MaxIter
    MaxIter = i

Debug=0
def set_debug(i):
    global Debug
    Debug = i

def log(var, i=1):
    if Debug >= i:
        print(repr(var))

def d(v):
    if v:
        import pudb
        pudb.set_trace()

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

from .vm import TrackerVM, Op
from .tstr import tstr

class EState(enum.Enum):
    # Char is when we find that the last character being compared is same as
    # the last character being inserted
    Char = enum.auto()
    # Last is when the last correction goes bad.
    Last = enum.auto()
    String = enum.auto()
    EOF = enum.auto()
    Skip = enum.auto()
    Unknown = enum.auto()

All_Characters = list(string.printable + string.whitespace)

def save_trace(traces, i, file='trace'):
    if Debug > 0:
        with open('.t/%s-%d.txt' % (file,i), 'w+') as f:
            [print(i, file=f) for i in traces]

class ExecFile(bex.ExecFile):
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
        others = []
        #if self.last_fix != self.checked_char:
        for i, t in enumerate(cmp_traces):
            if h.opA == t.opA:
                cmp_stack.append((i, t))
            else:
                others.append((i, t))
        #else:
        #    # Now, this is heuristics. What we really need is a tainting package
        #    # so that we can exactly track the comparisons on the last character
        #    # for now, we assume that the last successful match was probably
        #    # made on the last_fix
        #    assert False # to be disabled after verification.
        #    for i, t in enumerate(cmp_traces):
        #        success = False
        #        if h.opA == t.opA:
        #            if t.result: success = True
        #            if success:
        #                others.append((i, t))
        #            else:
        #                cmp_stack.append((i, t))
        #        else:
        #            others.append((i, t))

        return (cmp_stack, others)

    def extract_solutions(self, elt, lst_solutions, flip=False):
        fn = TrackerVM.COMPARE_OPERATORS[elt.opnum]
        result = fn(elt.opA, elt.opB)
        myfn = fn if not flip else lambda a, b: not fn(a, b)
        if result:
            lst = [c for c in lst_solutions if myfn(c, elt.opB)]
        else:
            lst = [c for c in lst_solutions if not myfn(c, elt.opB)]
        return lst


    def get_correction(self, cmp_stack):
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
        point_of_divergence = random.randrange(0, stack_size-1)
        #point_of_divergence = 0

        # if we dont get a solution by inverting the last comparison, go one
        # step back and try inverting it again.
        while point_of_divergence < stack_size:
            # now, we need to skip everything
            diverge, *satisfy = cmp_stack[point_of_divergence:]
            lst_solutions = All_Characters
            for i,elt in reversed(satisfy):
                assert elt.opA in [self.checked_char, self.last_fix]
                lst_solutions = self.extract_solutions(elt, lst_solutions, False)
            # now we need to diverge here
            i, elt = diverge
            assert elt.opA in [self.checked_char, self.last_fix]
            lst_solutions = self.extract_solutions(elt, lst_solutions, True)
            if lst_solutions:
                return lst_solutions
            point_of_divergence += 1

    def is_same_op(self, a, b):
        return a.opnum == b.opnum and a.opA == b.opA and a.opB == b.opB

    def kind(self, h):
        pred = TrackerVM.COMPARE_OPERATORS[h.opnum]
        cmp_result = pred(h.opA, h.opB)

        if Op(h.opnum) in [Op.EQ, Op.NE] and type(h.opB) is str and len(h.opB) > 1:
            return (1, EState.String, h)

        elif h.opA == self.checked_char:
            return (1, EState.Char, h)

        elif Op(h.opnum) in [Op.EQ, Op.IN, Op.NE, Op.NOT_IN] and h.opA == '':
            return (1, EState.EOF, h)

        elif h.opA in [self.last_fix, self.checked_char] and \
                Op(h.opnum) in [Op.IN, Op.EQ, Op.NOT_IN, Op.NE]:
            # if the comparison is eq or in and it succeeded and the character
            # compared was equal to last_fix, then this is the last match.
            return (1, EState.Last, (h, self.checked_char, self.last_fix))
        else:
            return (0, EState.Unknown, (h, self.checked_char, self.last_fix))

    def on_trace(self, i, vm, traces):
        # we are assuming a character by character comparison.
        # so get the comparison with the last element.
        h, *ltrace = traces
        self.last_iter_top = h
        self.result_of_last_op = TrackerVM.COMPARE_OPERATORS[h.opnum](h.opA, h.opB)

        idx, k, info = self.kind(h)
        log((i, idx, k, vm.steps, info))
        if k == EState.Char:
            # This was a character comparison. So collect all
            # comparisions made using this character. until the
            # first comparison that was made otherwise.
            cmp_stack, _ = self.comparisons_on_last_char(h, traces)
            # Now, try to fix the last failure
            self.next_opts = self.get_correction(cmp_stack)
            new_char = random.choice(self.next_opts)
            self.next_opts = [i for i in self.next_opts if i != new_char]
            arg = "%s%s" % (sys.argv[1][:-1], new_char)

            self.last_fix = new_char
            self.checked_char = None
            self.last_result = self.result_of_last_op
            self.saved_last_iter_top = self.last_iter_top
            return tstr(arg, idx=0)
        elif k == EState.Skip:
            # this happens when skipwhitespaces and similar are used.
            # the parser skips whitespaces, and compares the last
            # non-whitespace which may not be the last character inserted
            # if we had inserted a whitespace.
            # So the solution (for now) is to simply assume that the last
            # character matched.
            new_char = random.choice(All_Characters)
            arg = "%s%s" % (sys.argv[1], new_char)

            self.checked_char = new_char
            self.last_fix = None
            return tstr(arg, idx=0)
        elif k == EState.String:
            #assert h.opA == self.last_fix or h.opA == self.checked_char
            common = os.path.commonprefix(h.oargs)
            if self.checked_char:
                # if checked_char is present, it means we passed through
                # EState.EOF
                assert h.opB[len(common)-1] == self.checked_char
                arg = "%s%s" % (sys.argv[1], h.opB[len(common):])
            elif self.last_fix:
                assert h.opB[len(common)-1] == self.last_fix
                arg = "%s%s" % (sys.argv[1], h.opB[len(common):])

            self.last_fix = None
            self.checked_char = None
            return tstr(arg, idx=0)
        elif k == EState.EOF:
            new_char = random.choice(All_Characters)
            arg = "%s%s" % (sys.argv[1], new_char)

            self.checked_char = new_char
            self.last_fix = None
            self.last_result = self.result_of_last_op
            self.saved_last_iter_top = self.last_iter_top
            return tstr(arg, idx=0)
        elif k == EState.Last:
            # This was a character comparison. So collect all
            # comparisions made using this character. until the
            # first comparison that was made otherwise.
            cmp_stack, _ = self.comparisons_on_last_char(h, traces)
            # Now, try to fix the last failure
            self.next_opts = self.get_correction(cmp_stack)
            self.next_opts = [i for i in self.next_opts if i not in [self.last_fix, self.checked_char]]
            new_char = random.choice(self.next_opts)
            arg = "%s%s" % (sys.argv[1][:-1], new_char)

            self.last_fix = new_char
            self.checked_char = None
            self.last_result = self.result_of_last_op
            self.saved_last_iter_top = self.last_iter_top
        else:
            assert False

    def exec_code_object(self, code, env):
        self.last_fix = sys.argv[1][-2] if len(sys.argv[1]) > 1 else None
        # The last_character assignment made is the first character assigned
        # when starting.
        self.checked_char = sys.argv[1][-1]
        last_vm_step = 0

        for i in range(0, MaxIter):
            vm = TrackerVM()
            try:
                log(">> %s" % sys.argv)
                res = vm.run_code(code, f_globals=env)
                log("Arg: %s" % repr(sys.argv[1]), 0)
                return res
            except Exception as e:
                vm_step = vm.steps
                vm_step = last_vm_step
                traces = list(reversed(vm.get_trace()))
                save_trace(traces, i)
                save_trace(vm.byte_trace, i, file='byte')
                sys.argv[1] = self.on_trace(i, vm, traces)

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

        # making it easy!. We start with a space
        self.checked_char = tstr(random.choice(All_Characters), idx=0)
        new_argv = [args.prog] + [self.checked_char]
        if args.module:
            self.run_python_module(args.prog, new_argv)
        else:
            self.run_python_file(args.prog, new_argv)
