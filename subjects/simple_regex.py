#!/usr/bin/env python3
# From https://morepypy.blogspot.de/2010/05/efficient-and-elegant-regular.html

class Regex(object):
    def __init__(self, empty):
        # empty denotes whether the regular expression
        # can match the empty string
        self.empty = empty
        # mark that is shifted through the regex
        self.marked = False

    def reset(self):
        """ reset all marks in the regular expression """
        self.marked = False

    def shift(self, c, mark):
        """ shift the mark from left to right, matching character c."""
        # _shift is implemented in the concrete classes
        marked = self._shift(c, mark)
        self.marked = marked
        return marked


class Char(Regex):
    def __init__(self, c):
        Regex.__init__(self, False)
        self.c = c

    def _shift(self, c, mark):
        return mark and c == self.c

    def __str__(self):
        return self.c

    def __repr__(self):
        return "Char(\'" + str(self) + "\')"

class Epsilon(Regex):
    def __init__(self):
        Regex.__init__(self, empty=True)

    def _shift(self, c, mark):
        return False


class Binary(Regex):
    def __init__(self, left, right, empty):
        Regex.__init__(self, empty)
        self.left = left
        self.right = right

    def reset(self):
        self.left.reset()
        self.right.reset()
        Regex.reset(self)

class Alternative(Binary):
    def __init__(self, left, right):
        empty = left.empty or right.empty
        Binary.__init__(self, left, right, empty)

    def _shift(self, c, mark):
        marked_left  = self.left.shift(c, mark)
        marked_right = self.right.shift(c, mark)
        return marked_left or marked_right

    def __str__(self):
        return "(%s|%s)" % (str(self.left), str(self.right))

    def __repr__(self):
        return "Alternative(%s, %s)" % (repr(self.left), repr(self.right))

class Repetition(Regex):
    def __init__(self, re):
        Regex.__init__(self, True)
        self.re = re

    def _shift(self, c, mark):
        return self.re.shift(c, mark or self.marked)

    def reset(self):
        self.re.reset()
        Regex.reset(self)

    def __str__(self):
        return "(%s)*" % self.re

    def __repr__(self):
        return "Repetition(%s)" % (repr(self.re))

class Sequence(Binary):
    def __init__(self, left, right):
        empty = left.empty and right.empty
        Binary.__init__(self, left, right, empty)

    def _shift(self, c, mark):
        old_marked_left = self.left.marked
        marked_left = self.left.shift(c, mark)
        marked_right = self.right.shift(
            c, old_marked_left or (mark and self.left.empty))
        return (marked_left and self.right.empty) or marked_right

    def __str__(self):
        return str(self.left) + str(self.right)

    def __repr__(self):
        return "Sequence(%s, %s)" % (repr(self.left), repr(self.right))

def match(re, s):
    if not s:
        return re.empty
    # shift a mark in from the left
    result = re.shift(s[0], True)
    for c in s[1:]:
        # shift the internal marks around
        result = re.shift(c, False)
    re.reset()
    return result


#the compilation is not part of the original code

def find_next_closing_brace(string):
    i = 0
    brace_counter = 0
    while True:
        # in this case there is no closing brace for the alternative
        i += 1
        if i == len(string):
            break
        if string[i] == "(":
            brace_counter += 1
        if string[i] == ")":
            brace_counter -= 1
        if string[i] == ")" and brace_counter == -1:
            break
    return i

def compile(regex, stack, counter):
    if counter >= len(regex):
        return stack[-1][-1]
    c = regex[counter]

    stacktop = stack[-1]
    if c == "(":
        stack.append([])
        i = find_next_closing_brace(regex[counter:])
        compile(regex[counter + 1: counter + i], stack, 0)
        result = stack.pop().pop()
        if stacktop:
            seq = Sequence(stacktop.pop(), result)
        else:
            seq = result
        stacktop.append(seq)
        counter += i

    if c == ")":
        stack.pop()
        stack[-1].append(stacktop[-1])

    if c == "*":
        el = stacktop.pop()
        stacktop.append(Repetition(el))

    if c == "|":
        counter += 1
        i = find_next_closing_brace(regex[counter:])
        # compile right-hand side of Alternative
        rhs = compile(regex[counter:counter + i], [[]], 0)
        el = stacktop.pop()
        stacktop.append(Alternative(el, rhs))
        # if there was a closing bracket, we have to add a 1, otw. not
        counter = counter + i



    if c not in ["(", "|", "*", ")"]:
        if stacktop:
            el = stacktop.pop()
            stacktop.append(Sequence(el, Char(c)))
        else:
            stacktop.append(Char(c))

    return compile(regex, stack, counter + 1)



if __name__ == "__main__":
    import sys

    # regex = Sequence(Char('b'), Char('s'))
    regex = compile("((b((a|s)*))|c)*c", [[]], 0)
    # regex = compile("ab*", [[]], 0)
    print(repr(regex))
    # regex = Sequence(Char('{'), Sequence(Alternative(Alternative(Char('a'), Char('b')), Char('c')), Repetition(Sequence(Char('d'), Char('e')))))
    if not match(regex, sys.argv[1]):
        raise ValueError("Input string does not match regex")

    print(match(regex, sys.argv[1]))
