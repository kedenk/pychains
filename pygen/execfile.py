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

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

from .vm import TrackerVM, Op
from .tstr import tstr

class Matched(enum.Enum):
    Last = enum.auto()
    String = enum.auto()
    Char = enum.auto()
    Skip = enum.auto()

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
        if self.last_fix != self.checked_char:
            for i, t in enumerate(cmp_traces):
                if h.opA == t.opA:
                    cmp_stack.append((i, t))
                else:
                    others.append((i, t))
        else:
            # Now, this is heuristics. What we really need is a tainting package
            # so that we can exactly track the comparisons on the last character
            # for now, we assume that the last successful match was probably
            # made on the last_fix
            assert False # to be disabled after verification.
            for i, t in enumerate(cmp_traces):
                success = False
                if h.opA == t.opA:
                    if t.result: success = True
                    if success:
                        others.append((i, t))
                    else:
                        cmp_stack.append((i, t))
                else:
                    others.append((i, t))

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
        point = random.randrange(0, stack_size)
        # now, we need to skip everything
        diverge, *satisfy = cmp_stack[point:]
        lst_solutions = All_Characters
        for i,elt in reversed(satisfy):
            assert elt.opA == self.checked_char
            lst_solutions = self.extract_solutions(elt, lst_solutions, False)
        # now we need to diverge here
        i, elt = diverge
        assert elt.opA == self.checked_char
        lst_solutions = self.extract_solutions(elt, lst_solutions, True)
        return lst_solutions

    def kind(self, t):
        if t.opA == self.checked_char and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) == False:
            return (1, Matched.Char)
        elif Op(t.opnum) in [Op.EQ, Op.IN] and t.opA == '' and t.opB != '' and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) == False:
            # if opA is empty, and it is being compared to non empty then
            # the last char added matched
            return (1, Matched.Last)
        elif Op(t.opnum) == Op.EQ and t.opA == '' and t.opB == ''  and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) == True:
            return (2, Matched.Last)
        elif Op(t.opnum) == Op.EQ and type(t.opB) is str and len(t.opB) > 1 and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) == False:
            return (1, Matched.String)
        elif t.opA == self.last_fix and Op(t.opnum) in [Op.IN, Op.EQ] and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) != self.last_result:
            # if the comparison is eq or in and it succeeded and the character
            # compared was equal to last_fix, then this is the last match.
            return (3, Matched.Last)
        elif t.opA == self.checked_char and Op(t.opnum) in [Op.IN, Op.EQ] and \
            TrackerVM.COMPARE_OPERATORS[t.opnum](t.opA, t.opB) == True:
            return (4 ,Matched.Last)
        else:
            print(t)
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
                print(">> %s" % sys.argv)
                res = vm.run_code(code, f_globals=env)
                print("Result: %s" % sys.argv)
                return res
            except Exception as e:
                # Ensure progress
                vm_step = vm.steps
                assert vm_step > last_vm_step
                vm_step = last_vm_step
                # TODO: As of now, we assume that the character we appended:
                # the update_char actually is sufficient to get us through this
                # character check. But this may not hold in every case,
                # particularly if the character at a position has to satisfy
                # multiple checks. This needs to be fixed later.
                traces = list(reversed(vm.get_trace()))
                save_trace(traces, i)
                save_trace(vm.byte_trace, i, file='byte')
                # we are assuming a character by character comparison.
                # so get the comparison with the last element.
                h, *ltrace = traces
                self.result_of_last_op = TrackerVM.COMPARE_OPERATORS[h.opnum](h.opA, h.opB)

                i, k = self.kind(h)
                print(i, k, vm.steps)
                if k == Matched.Char:
                    # This was a character comparison. So collect all
                    # comparisions made using this character. until the
                    # first comparison that was made otherwise.
                    cmp_stack, _ = self.comparisons_on_last_char(h, ltrace)
                    # Now, try to fix the last failure
                    possible_new_chars = self.get_correction(cmp_stack)
                    new_char = random.choice(possible_new_chars)
                    arg = "%s%s" % (sys.argv[1][:-1], new_char)
                    sys.argv[1] = tstr(arg, idx=0)

                    self.last_fix = new_char
                    self.checked_char = None
                    self.last_result = self.result_of_last_op
                elif k == Matched.Skip:
                    # this happens when skipwhitespaces and similar are used.
                    # the parser skips whitespaces, and compares the last
                    # non-whitespace which may not be the last character inserted
                    # if we had inserted a whitespace.
                    # So the solution (for now) is to simply assume that the last
                    # character matched.
                    new_char = random.choice(All_Characters)
                    arg = "%s%s" % (sys.argv[1], new_char)
                    sys.argv[1] = tstr(arg, idx=0)

                    self.checked_char = new_char
                    self.last_fix = None
                elif k == Matched.String:
                    #assert h.opA == self.last_fix or h.opA == self.checked_char
                    common = os.path.commonprefix(h.oargs)
                    if self.checked_char:
                        # if checked_char is present, it means we passed through
                        # Matched.Last
                        assert h.opB[len(common)-1] == self.checked__char
                        arg = "%s%s" % (sys.argv[1], h.opB[len(common):])
                    elif self.last_fix:
                        assert h.opB[len(common)-1] == self.last_fix
                        arg = "%s%s" % (sys.argv[1], h.opB[len(common):])
                    sys.argv[1] = tstr(arg, idx=0)

                    self.last_fix = None
                    self.checked_char = None
                elif k == Matched.Last:
                    new_char = random.choice(All_Characters)
                    arg = "%s%s" % (sys.argv[1], new_char)
                    sys.argv[1] = tstr(arg, idx=0)

                    self.checked_char = new_char
                    self.last_fix = None
                else:
                    assert False
            pass

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
