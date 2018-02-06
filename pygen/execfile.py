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

# TODO: Any kind of preprocessing -- space strip etc. distorts the processing.

from .vm import TrackerVM, Op

class Matched(enum.Enum):
    Last = enum.auto()
    String = enum.auto()
    Char = enum.auto()

String_List = list(string.printable + string.whitespace)

class ExecFile(bex.ExecFile):
    def get_cmp_char(self, oargs, last = False):
        opA, opB = oargs
        # We assume that the comparison is char == '?' or char in [...]
        if last:
            if opA == '':
                # it is because we successfully matched the first char.
                return (True, opA)
        cmp_char = opA
        return (False, cmp_char)

    def is_string(self, arg):
        return len(arg) > 1

    def get_comparisons_on_last_char(self, cmp_traces):
        """
        The idea is to get a list of all comparisons made to the last character.
        """
        last_cmp = cmp_traces[-1]
        op, oargs, result, line = last_cmp
        # For now, we assume that the comparison is of the kind
        # last_char in {set}
        # or
        # last_char == char_const
        # that is last_char is the first argument in the oargs array.
        last_char, cmp_args = oargs

        if self.is_string(last_char):
            # if it is actually a string rather than a character,
            return (Matched.String, [(op, oargs, result, line)], [], [])

        matched_last_char, cmp_char = self.get_cmp_char(oargs, last=True)
        # if the comparison is being made not with the last_char, but with
        # an empty string, it means that the last comparisoin succeeded, and
        # we are past the end.
        if matched_last_char:
            return (Matched.Last, [], [], [])

        # If the last character was matched successfully, we may need
        # to save and incorporate that in the update_char filter
        failed_last_ops, successful_last_ops, others = [], [], []
        for (op, oargs, result, line) in reversed(cmp_traces):
            _, char = self.get_cmp_char(oargs)
            if cmp_char == char:
                if result:
                    successful_last_ops.append((op, oargs, result, line))
                else:
                    failed_last_ops.append((op, oargs, result, line))
            else:
                others.append((op, oargs, result, line))

        return (Matched.Char, failed_last_ops, successful_last_ops, others)


    def filter_match(self, last_cmp, success_cmp, invert=False):
        op, oargs, r, l = last_cmp
        fn = pvm.VirtualMachine.COMPARE_OPERATORS[op.value]
        if invert:
            matches = [i for i in String_List if not fn(i, oargs[1])]
        else:
            matches = [i for i in String_List if fn(i, oargs[1])]

        # make sure that the success_cmp remain success
        new_matches = matches
        for sop, soargs, _, sl in success_cmp:
            sfn = pvm.VirtualMachine.COMPARE_OPERATORS[sop.value]
            new_matches = [i for i in new_matches if sfn(i, soargs[1])]

        return new_matches, l

    def produce_filtered_values(self, f_cmps, s_cmps):
        # we have a list of comparisons made to the last character.
        # Choose a random comparison, and then choose a random character
        # that satisfies that comparison.
        updates = []
        for last_cmp in f_cmps:
            update, l = self.filter_match(last_cmp, s_cmps)
            if update:
                update_char = random.choice(update)
                updates.append((update_char, l))
        if updates:
            return random.choice(updates)
        # try one of the successes
        for last_cmp in s_cmps:
            update, l = self.filter_match(last_cmp, [], invert=True)
            if update:
                update_char = random.choice(update)
                updates.append((update_char, l))
        return random.choice(updates)


    def exec_code_object(self, code, env):
        for i in range(0, MaxIter):
            vm = TrackerVM()
            try:
                print(">> %s" % sys.argv)
                res = vm.run_code(code, f_globals=env)
                print("Result: %s" % sys.argv)
                return res
            except Exception as e:
                # TODO: As of now, we assume that the character we appended:
                # the update_char actually is sufficient to get us through this
                # character check. But this may not hold in every case,
                # particularly if the character at a position has to satisfy
                # multiple checks. This needs to be fixed later.
                traces = vm.get_trace()
                # we are assuming a character by character comparison.
                # so get the comparison with the last element.
                m, f_cmps, s_cmps, o = self.get_comparisons_on_last_char(traces)
                if m == Matched.Last:
                    self.next_char = random.choice(String_List)
                    arg = "%s%s" % (sys.argv[1], self.next_char)
                elif m == Matched.String:
                    op, oargs, result, line = f_cmps[0]
                    common = os.path.commonprefix(oargs)
                    assert oargs[0][len(common)] == self.next_char
                    arg = "%s%s" % (sys.argv[1][:-1], oargs[1][len(common):])
                else:
                    # *_cmps contains all the comaparisons made to the last
                    # letter. Pick a random comparison made, and a random
                    # satisfying char.
                    # Assume that update_char will satisfy all comparisons made
                    # until then.
                    update_char, l = self.produce_filtered_values(f_cmps, s_cmps)
                    self.next_char = random.choice(String_List)
                    arg = "%s%s%s" % (sys.argv[1][:-1], update_char, self.next_char)
                sys.argv[1] = arg

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
        self.next_char = random.choice(String_List)
        new_argv = [args.prog] + [self.next_char]
        print(">> %s" % new_argv)
        if args.module:
            self.run_python_module(args.prog, new_argv)
        else:
            self.run_python_file(args.prog, new_argv)
