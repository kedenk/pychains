"""A pure-Python Python bytecode interpreter."""
# Based on:
# pyvm2 by Paul Swartz (z3p), from http://www.twistedmatrix.com/users/z3p/

from __future__ import print_function, division

from bytevm.pyvm2 import VirtualMachine
import bytevm.sys as sys
from enum import Enum
from random import shuffle
import string
import exrex
from .tstr import tstr

class Operator(Enum):
    LT = 0
    LE = 1
    EQ = 2
    NE = 3
    GT = 4
    GE = 5
    IN = 6
    NOT_IN = 7
    IS = 8
    IS_NOT = 9
    ISSUBCLASS = 10

class Functions(Enum):
    starting_value = 10
    find_str = 11
    split_str = 12
    match_sre = 13
    find_tstr = 14
    split_tstr = 15


class GetComparisons(VirtualMachine):

    def functions(self):
        self.functions = [
            "find of str",
            "split of str",
            "match of _sre.SRE_Pattern",
            "method tstr.find",
            "method tstr.split"
        ]


    def __init__(self):
        # The call stack of frames.
        #self.frames = []
        # The current frame.
        #self.frame = None
        #self.return_value = None
        #self.last_exception = None
        self.args = sys.argv[1:]
        self.load_from = None # indicates from which object the last function was loaded
        self.functions()
        super().__init__()

        self.trace = list()
        # stores the lines seen throughout all executions, is not cleared after one execution
        self.lines_seen = set()
        # TODO it might also be worth storing the new comps and exploring inputs based on those new comps first
        self.new_comp_seen = False

        #some constants that may be configured in the future
        self.expand_in = 2 # sets how many values are taken from the right hand side at most when a call to in or not in happens

    def clean(self, new_args):
        self.args = new_args
        self.trace = list()
        self.load_from = None
        self.frame = None
        self.return_value = None
        self.last_exception = None
        self.frames = []

        self.new_comp_seen = False


    def topn(self, n):
        """Get a number of values from the value stack.

        A list of `n` values is returned, the deepest value first.

        """
        if n:
            ret = self.frame.stack[-n:]
            return ret
        else:
            return []


    def byte_IMPORT_NAME(self, name):
        if name == 'io':
            super().byte_IMPORT_NAME('myio')
            r = self.frame.stack[-1]
            r.__name__ == 'io'
        elif name == 're':
            super().byte_IMPORT_NAME('rxpy.re')
            r = self.frame.stack[-1]
            r.__name__ == 're'
        else:
            super().byte_IMPORT_NAME(name)


    def byte_COMPARE_OP(self, opnum):
        self.line_already_seen()
        operands = self.topn(2)
        for arg in self.args:
            if ((str(operands[0]) != '') and str(operands[0]) in arg) \
                    or ((str(operands[1]) != '') and str(operands[1]) in arg)\
                    or type(operands[0]) is tstr or type(operands[1]) is tstr:
                self.trace.append((Operator(opnum), operands))
                break

            # we also have to consider, that a character is looked for, which is not in the arg, e.g. "'?' in arg"

        return VirtualMachine.byte_COMPARE_OP(self, opnum)


    def line_already_seen(self):
        line = (self.frame.f_lineno, self.frame.f_lasti)
        if line not in self.lines_seen:
            self.new_comp_seen = True
            self.lines_seen.add(line)



    def function_watched(self, function_string):
        counter = 0
        for f in self.functions:
            if f in function_string:
                return counter
            counter += 1
        return -1


    def call_function(self, arg, func_args, kwargs):
        self.line_already_seen()
        args = self.topn(arg + 1)
        func_watched = self.function_watched(str(args[0]))
        if func_watched != -1:
            self.trace.append((Functions(Functions.starting_value.value + func_watched + 1), [self.load_from] + args))

        return VirtualMachine.call_function(self, arg, func_args, kwargs)


    def byte_LOAD_ATTR(self, attr):
        self.line_already_seen()
        obj = self.top()
        self.load_from = obj

        return VirtualMachine.byte_LOAD_ATTR(self, attr)


    #################    Next input generation     ############################

    # lets first use a simple approach where strong equality is used for replacement in the first input
    # also we use parts of the rhs of the in statement as substitution
    def get_next_inputs(self, pos, Track):
        next_inputs = list()
        current = self.args[0]
        length_next_inputs = 0
        comparisons = list()
        for t in self.trace:
            if t[0] == Operator.EQ or t[0] == Operator.NE:
                next_inputs += self.eq_next_inputs(t, current, pos, comparisons, Track)
            elif t[0] == Operator.IN or t[0] == Operator.NOT_IN:
                next_inputs += self.in_next_inputs(t, current, pos, comparisons, Track)
            elif t[0] == Functions.find_str or t[0] == Functions.find_tstr:
                next_inputs += self.str_find_next_inputs(t, current, pos, comparisons, Track)
            elif t[0] == Functions.split_str or t[0] == Functions.split_tstr:
                next_inputs += self.str_split_next_inputs(t, current, pos, comparisons, Track)
            elif t[0] == Functions.match_sre:
                next_inputs += self.match_sre_next_inputs(t, current, pos, comparisons)

            if len(next_inputs) > length_next_inputs:
                length_next_inputs = len(next_inputs)
                comparisons.append(t)

        # add some letter as substitution as well
        # if nothing else was added, this means, that the character at the position under observation did not have a
        # comparison, so we do also not add a "B", because the prefix is likely already completely wrong
        if next_inputs:
            next_inputs += [(0, pos, pos + 1, "B", comparisons, current)]
        return next_inputs


    # appends a new input based on the current checking position, the subst. and the value which was used for the run
    # the next position to observe will lie directly behind the substituted position
    def append_new_input(self, next_inputs, pos, subst, current, comparisons):
        next_inputs.append((0, pos, pos + len(subst), subst, comparisons, current))
        # if the character under observation lies in the middle of the string, it might be that we fulfilled the
        # constraint and should now start with appending stuff to the string again (new string will have length of
        # current plus length of the substitution minus 1 since the position under observation is substituted)
        if pos < len(current) - 1:
            next_inputs.append((0, pos, len(current) + len(subst) - 1, subst, comparisons, current))


    # apply the substitution for equality comparisons
    # TODO find all occ. in near future
    def eq_next_inputs(self, trace_line, current, pos, comparisons, Track):
        compare = trace_line[1]
        next_inputs = list()
        # if we use taint tracking, use another approach
        if Track:
            # check if the position that is currently watched is part of the taint
            if type(compare[0]) is tstr and compare[0].get_first_mapped_char() + len(compare[0]) >= pos:
                self.append_new_input(next_inputs, pos, compare[1], current, comparisons)
            elif type(compare[1]) is tstr and compare[1].get_first_mapped_char() + len(compare[1]) >= pos:
                self.append_new_input(next_inputs, pos, compare[0], current, comparisons)
            else:
                return[]
            return next_inputs

        # verify that both operands are string
        if type(compare[0]) is not str or type(compare[1]) is not str:
            return []
        cmp0_str = str(compare[0])
        cmp1_str = str(compare[1])
        if compare[0] == compare[1]:
            return []

        # self.changed.add(str(trace_line))
        find0 = current.find(cmp0_str)
        find1 = current.find(cmp1_str)
        # check if actually the char at the pos we are currently checking was checked in the comparison
        if find0 == pos:
            self.append_new_input(next_inputs, pos, cmp1_str, current, comparisons)
        elif find1 == pos:
            self.append_new_input(next_inputs, pos, cmp0_str, current, comparisons)

        return next_inputs


    # apply the subsititution for the in statement
    def in_next_inputs(self, trace_line, current, pos, comparisons, Track):
        compare = trace_line[1]
        next_inputs = list()
        if Track:
            # check if the position that is currently watched is part of the taint
            if type(compare[0]) is tstr and compare[0].get_first_mapped_char() + len(compare[0]) >= pos:
                counter = 0
                for cmp in compare[1]:
                    if compare[0] == cmp:
                        continue
                    if counter > self.expand_in:
                        break
                    counter += 1
                    self.append_new_input(next_inputs, pos, cmp, current, comparisons)
            elif self.check_in_tstr(compare[1], pos, compare[0]):
                self.append_new_input_non_direct_replace(next_inputs, current, compare[0], pos, comparisons)
            else:
                return[]
            return next_inputs
        # the lhs must be a string
        if type(compare[0]) is not str:
            return []
        cmp0_str = str(compare[0])
        counter = 0
        # take some samples from the collection in is applied on
        for cmp in compare[1]:
            # only take a subset of the rhs (the collection in is applied on)
            # TODO in some cases it is important to take the whole content of a collection into account
            if counter >= self.expand_in:
                break
            counter += 1
            cmp1_str = str(cmp)
            if compare[0] == cmp:
                continue
            # self.changed.add(str(trace_line))
            find0 = current.find(cmp0_str)
            if find0 == pos:
                self.append_new_input(next_inputs, pos, cmp1_str, current, comparisons)

        # it could also be, that a char is searched in the rhs, if this is the case, we have to handle this like in find
        # but only if the lhs is not the char under observation and only if the char we look for does not already exist
        # in the string we are searching
        # concretely we check if the rhs is a substring of the current input, if yes we are looking for something in the
        # current input
        check_char = current[pos]
        if not next_inputs and self.check_in_string(compare[1], current, check_char, cmp0_str):
            self.append_new_input_non_direct_replace(next_inputs, current, cmp0_str, pos, comparisons)

        return next_inputs

    # checks if the lhs is not in comp, comp is a non-empty string which is in current and the check_char must also
    # be in current
    def check_in_string(self, comp, current, check_char, lhs):
        return type(comp) is str and lhs not in comp \
                and comp != '' and comp in current and check_char in comp

    # checks if the lhs is not in comp, comp is a non-empty string which is in current and the check_char must also
    # be in current for tstr
    def check_in_tstr(self, comp, pos, lhs):
        return type(comp) is tstr and lhs not in comp \
                and str(comp) != '' and comp.get_first_mapped_char() + len(comp) >= pos

    def str_split_next_inputs(self, t, current, pos, comparisons, Track):
        # split is the same as find, but it may have a parameter which defines how many splits should be performed,
        # this does not interest us at the moment
        # TODO in future take the number of splits into account
        try:
            t[1][3] = 0
        except:
            pass
        return self.str_find_next_inputs(t, current, pos, comparisons, Track)

    def str_find_next_inputs(self, t, current, pos, comparisons, Track):
        # t[1][2] is the string which is searched for in the input, replace A with this string
        input_string = t[1][2]
        beg = 0
        end = len(t[1][0])
        next_inputs = list()
        try:
            beg = t[1][3]
            end = t[1][4]
        except:
            pass
        #search in the string for the value the program is looking for, if it exists, we are done here
        # also if the position to check is not in the string we are searching, we can stop here
        check_char = current[pos]
        if Track:
            # check if the position that is currently watched is part of the taint
            if self.check_in_tstr(t[1][0][beg:end], pos, input_string):
                next_inputs = self.append_new_input_non_direct_replace(next_inputs, current, input_string, pos, comparisons)

            return next_inputs

        if not self.check_in_string(t[1][0][beg:end], current, check_char, input_string):
            return []
        # here we have to handle the input appending ourselves since we have a special case
        # replace the position under observation with the new input string and ...
        next_inputs = self.append_new_input_non_direct_replace(next_inputs, current, input_string, pos, comparisons)
        return next_inputs

    # instead of replacing the char under naively, we replace the char and either look at the positions specified below
    def append_new_input_non_direct_replace(self, next_inputs, current, input_string, pos, comparisons):
        # set the next position behind what we just replaced
        next_inputs.append((0, pos, pos + len(input_string), input_string, comparisons, current))
        # set the next position in front of what we just replaced
        next_inputs.append((0, pos, pos, input_string, comparisons, current))
        # set the next position at the end of the string, s.t. if we satisfied something, we can restart appending
        # it may be that the replacement we did beforehand already sets the next pos to the end, then we do not need to
        # add a new position here
        if (pos + len(input_string) != len(current)):
            next_inputs.append((0, pos, len(current), input_string, comparisons, current))
        return next_inputs


    def match_sre_next_inputs(self, trace_line, current, pos, comparisons):
        pattern = trace_line[1][0].pattern
        string = exrex.getone(pattern)
        # we use A as the char which is checked against, so at at this point we should
        string = string.replace("A","B")
        # TODO replacement needs to be done on the whole string that is tried to be matched, this feature
        # needs to be implemented

        # TODO also we should check if the string was matched, if yes we should replace with something non-matching

        # TODO actually the best idea would be to see where the regex fails first and only replace the failing suffix

        # TODO also we have to think about optional creations, so in the end we should think about how to produce
        # strings properly from the regex
        next_inputs = list()
        to_match = trace_line[1][2]
        if to_match in current:
            match_pos = current.find(to_match)
            # from the current input cut out whatever was tried to be matched and replace it later with what was
            # tried to be matched (i.e. a representative of the regex), therefore the A is still included
            new_current = current[ :match_pos] + "A" + current[match_pos + len(to_match):]
            pos = match_pos
            self.append_new_input(next_inputs, pos, string, new_current, comparisons)
        return next_inputs