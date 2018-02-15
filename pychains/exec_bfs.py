"""Execute files of Python code."""

import imp
import os
import sys
import tokenize
import queue
import string
import random
import json

from .vm_bfs import GetComparisons, Operator, Functions

# This code is ripped off from coverage.py.  Define things it expects.
try:
    open_source = tokenize.open     # pylint: disable=E1101
except:
    def open_source(fname):
        """Open a source file the best way."""
        return open(fname, "rU")

NoSource = Exception

class Node:

    # parent is an object of class Node
    # change is a tuple of a position and a string. This tuple is used to determine a substitution
    # parentstring is the string which caused the generation of this specific node
    def __init__(self, parent, change):
        self.children = []
        self.parent = parent
        self.change = change
        self.parentstring = change[5]


    # gets a list of children to add to this node
    def addChildren(self, children):
        self.children += children

    # returns the next child in list and removes this object from the list
    def get_next_child(self):
        return self.children.pop(0)

    # checks if there are still children in the list
    def child_exists(self):
        return self.children

    # replaces at changepos the char with the given replacement in the parentstring
    # the tuple looks like
    #   (heuristic value,
    #   change_position,
    #   position for new observation,
    #   string used for replacement,
    #   list of comparisons made on the char under observation,
    #   string that was used as input for the parent which lead to the production of this Node)
    #
    # the heursitic value is currently not used but might be in future
    def get_substituted_string(self):
        return self.parentstring[0:self.change[1]] + self.change[3] + self.parentstring[self.change[1] + 1:]

    # returns a new input by substituting the change position and adding a new char at the next position that should be observed
    def get_next_input(self):
        next_input = self.get_substituted_string()
        return next_input[:self.change[2]] + "A" + next_input[self.change[2]:]

    # returns the position of the character under observation
    def get_observation_pos(self):
        return self.change[2]

    # returns the position that is substituted
    def get_subst_pos(self):
        return self.change[1]

    # returns the comparisons made on the position that is substituted
    def get_comparisons(self):
        return self.change[4]

    # returns the string that is used for the substitution
    def get_string_of_subsitution(self):
        return self.change[3]


# this is a constant which defines how many parents are checked for an equal comparison chain of the last character
comparison_equality_chain = 3

def exec_code_object_bfs(code, env, next_input):
    random.seed(42)
    vm = GetComparisons()
    # I currently assume that the string does only contain one 'A', therefore all existing A's are placed with B's
    next_input = str(next_input).replace("A","B") + "A"
    # start with some dummy node, the given substitution has no further effect
    current_Node = Node(None, (0, 0, len(next_input) - 1, 'B', [], 'A'))
    node_list = []

    already_seen = set()
    with open("outputs.txt","w") as outputs:
        # do not fun infinitely long, in future we might want to add some stopping criterion here
        for i in range(1, 3000000):
            # TODO add duplicate pruning

            #prepare the VM for running on the given input
            sys.argv[1] = next_input
            # outputs.write(next_input + "\n")
            vm.clean([next_input])
            current_change_pos = current_Node.get_observation_pos()
            print("#############")
            # we might run into exceptions since we produce invalid inputs
            # we catch those exceptions and produce a new input based on the gained knowledge through the
            # execution
            print(repr(next_input))

            # run the VM
            try:
                vm.run_code(code, f_globals=env)
            except Exception as e:
                print(e)

            # get the next inputs from the VM based on the trace
            next_inputs = vm.get_next_inputs(current_Node.get_observation_pos())

            # create nodes from the retrieved replacements
            node_list_append = list()
            for input in next_inputs:
                node_list_append.append(Node(current_Node, input))

            # random.shuffle(node_list_append)
            # filter for inputs, that do not lead to success, i.e. inputs that are already correct and inputs that
            # can be pruned in another form (see prune_input for more information)
            for node in list(node_list_append):
                if prune_input(node):
                    node_list_append.remove(node)
                    continue
                if check_seen(already_seen, node):
                    node_list_append.remove(node)
                    continue
                if not check_exception(node, vm, code, env):
                    node_list_append.remove(node)
                    # comparisons = print_comp(node)
                    # outputs.write("{\n\t\"" + node.get_substituted_string() +"\":{\n" + comparisons + "\n}\n")
                    outputs.write(repr(node.get_substituted_string()) + "\n")
                    print("Arg: " + repr(node.get_substituted_string()))
                    return

            # add the surviving nodes to the current node, since those are its children
            current_Node.addChildren(node_list_append)

            # for breadth first search, the nodelist is expanded
            node_list += node_list_append

            # get the next node which has a child which can be used to expand further
            # while current_Node is not None and not current_Node.child_exists():
            #     current_Node = current_Node.parent
            if not node_list:
                print("There is nothing we can do for you, something seems to be broken earlier.")
                print("Restart with minimal string")
                next_input = "A"
                current_Node = Node(None, (0, 0, 0, 'B', [], 'A'))
                continue

            current_Node = node_list.pop(0)

            # if current_Node == None:
            #     return

            # get the child and use it for the next expansion
            # current_Node = current_Node.get_next_child()

            # get the next input based on the substitution stored in the current node
            next_input = current_Node.get_next_input()
            pass


# for inputs with length greater 3 we can assume that if
# it ends with a value which was not successful for a small input
def prune_input(node):
    s = node.get_substituted_string()
    # we do not need to create arbitrarily long strings, such a thing will likely end in an infinite
    # string, so we prune branches starting here
    if "BBBA" in node.get_next_input():
        return True
    if len(s) <= 3:
        return False
    # print(repr(s), repr(s[0:len(s) // 2]), repr(s[len(s) // 2:]))
    if s[len(s)//2:].endswith(s[0:len(s)//2]):
        return True
    if comparison_chain_equal(node):
        return True
    return False

# TODO this can be done just on the parent instead of checking for all children
def comparison_chain_equal(node):
    global comparison_equality_chain
    initial_trace = node.get_comparisons()
    for i_eq in range(0,comparison_equality_chain):
        if node.parent is None:
            return False
        node = node.parent
        cmp_trace = node.get_comparisons()
        if len(cmp_trace) != len(initial_trace):
            return False
        i = 0
        for i in range(0, len(cmp_trace)):
            cmp = cmp_trace[i]
            init = initial_trace[i]
            if cmp != init:
                if not compare_predicates_in_detail(cmp, init):
                    return False
    return True


# checks if two predicates are equal for some special cases like in or special function calls
def compare_predicates_in_detail(cmp, init):
    if cmp[0] == init[0]:
        # for split and find on string check if the value to look for is the same, if yes return true
        if cmp[0] in [Functions.split_str, Functions.find_str]:
            return cmp[1][-1] == cmp[1][-1]
        if cmp[0] in [Operator.IN, Operator.NOT_IN]:
            return False
    return False

#check if the input is already in the queue, if yes one can just prune it at this point
def check_seen(already_seen, node):
    s = node.get_next_input()
    if s in already_seen:
        return True
    already_seen.add(node.get_next_input())


# check if an input causes a crash, if not it is likely successful and can be reported
#TODO this is currently quite inefficient, since we run the prog on each input twice, should be changed in future
def check_exception(node, vm, code, env):
    next_input = node.get_substituted_string()
    sys.argv[1] = next_input
    vm.clean([next_input])

    try:
        vm.run_code(code, f_globals=env)
    except Exception:
        return True

    return False


def print_comp(node):
    objects = list()
    while node.parent is not None:
        comps = "["
        for cmp in node.get_comparisons():
            comps += "{\"" + cmp[0].name + "\":["
            for arg in cmp[1]:
                comps += "\"" + str(arg) + "\","
            # remove last comma
            comps = comps[:-1]
            comps += "]},"
        comps = comps[:-1]
        comps += "]"
        object = "{\"%s\":[\"%s\",%s]}" % (node.get_subst_pos(), node.get_string_of_subsitution(), comps)
        objects.append(object)
        node = node.parent
    result = "["
    for obj in reversed(objects):
        result += obj + ","
    result = result[:-1]
    result += "]"
    return json.dumps(json.loads(result), indent= 2)






def calc_heuristic(expansion_counter, vm, input_string):
    result = sys.maxsize // 2

    # earlier expansions should be prioritized
    # inputs that are created based on later comparisons might be deeper down in the program and should therefore
    # be preferred
    result += expansion_counter
    # longer traces indicate more execution, so likely the input was more correct
    # result -= len(vm.trace)
    # inputs that do not produce an exception might be correct, so we prefer it by some constant
    # if vm.last_exception is None:
    #     result -= 20
    # shorter inputs are preferred at the moment
    # result += len(input_string)

    # a higher levensthein distance is better
    # result -= len(set("qiaup98bsdf") & set(input_string)) * 4

    # prefer inputs with many control characters (non-alpha nums)
    # result -= sum((not c.isalnum() and c not in {"\n", "\t", "\r", "\f"}) for c in input_string)

    # the number of successful comparisons should directly correlate with how good an input is
    # result -= get_successful_equality_comparisons(vm.trace)

    # check if new comparisons where explored with this input, if yes, it might be worth checking this input in more
    # detail
    if vm.new_comp_seen:
        result -= 20

    return result


# get the number of successful equality comparisons in a trace
def get_successful_equality_comparisons(trace):
    counter = 0
    for t in trace:
        if t[0] == Operator.EQ:
            if t[1][0] == t[1][1]:
               counter += 1
    return counter



# TODO: we need a more sophisicated restart function in future
def restart():
    return "qiaup98bsdf"


# from coverage.py:

try:
    # In Py 2.x, the builtins were in __builtin__
    BUILTINS = sys.modules['__builtin__']
except KeyError:
    # In Py 3.x, they're in builtins
    BUILTINS = sys.modules['builtins']


def rsplit1(s, sep):
    """The same as s.rsplit(sep, 1), but works in 2.3"""
    parts = s.split(sep)
    return sep.join(parts[:-1]), parts[-1]


def run_python_module(modulename, args):
    """Run a python module, as though with ``python -m name args...``.

    `modulename` is the name of the module, possibly a dot-separated name.
    `args` is the argument array to present as sys.argv, including the first
    element naming the module being executed.

    """
    openfile = None
    glo, loc = globals(), locals()
    try:
        try:
            # Search for the module - inside its parent package, if any - using
            # standard import mechanics.
            if '.' in modulename:
                packagename, name = rsplit1(modulename, '.')
                package = __import__(packagename, glo, loc, ['__path__'])
                searchpath = package.__path__
            else:
                packagename, name = None, modulename
                searchpath = None  # "top-level search" in imp.find_module()
            openfile, pathname, _ = imp.find_module(name, searchpath)

            # Complain if this is a magic non-file module.
            if openfile is None and pathname is None:
                raise NoSource(
                    "module does not live in a file: %r" % modulename
                    )

            # If `modulename` is actually a package, not a mere module, then we
            # pretend to be Python 2.7 and try running its __main__.py script.
            if openfile is None:
                packagename = modulename
                name = '__main__'
                package = __import__(packagename, glo, loc, ['__path__'])
                searchpath = package.__path__
                openfile, pathname, _ = imp.find_module(name, searchpath)
        except ImportError:
            _, err, _ = sys.exc_info()
            raise NoSource(str(err))
    finally:
        if openfile:
            openfile.close()

    # Finally, hand the file off to run_python_file for execution.
    args[0] = pathname
    run_python_file(pathname, args, package=packagename)


def run_python_file(filename, args, package=None):
    """Run a python file as if it were the main program on the command line.

    `filename` is the path to the file to execute, it need not be a .py file.
    `args` is the argument array to present as sys.argv, including the first
    element naming the file being executed.  `package` is the name of the
    enclosing package, if any.

    """
    # Create a module to serve as __main__
    old_main_mod = sys.modules['__main__']
    main_mod = imp.new_module('__main__')
    sys.modules['__main__'] = main_mod
    main_mod.__file__ = filename
    if package:
        main_mod.__package__ = package
    main_mod.__builtins__ = BUILTINS

    # Set sys.argv and the first path element properly.
    old_argv = sys.argv
    old_path0 = sys.path[0]
    sys.argv = args
    if package:
        sys.path[0] = ''
    else:
        sys.path[0] = os.path.abspath(os.path.dirname(filename))

    try:
        # Open the source file.
        try:
            source_file = open_source(filename)
        except IOError:
            raise NoSource("No file to run: %r" % filename)

        try:
            source = source_file.read()
        finally:
            source_file.close()

        # We have the source.  `compile` still needs the last line to be clean,
        # so make sure it is, then compile a code object from it.
        if not source or source[-1] != '\n':
            source += '\n'
        code = compile(source, filename, "exec")

        # Execute the source file.
        exec_code_object(code, main_mod.__dict__)
    finally:
        # Restore the old __main__
        sys.modules['__main__'] = old_main_mod

        # Restore the old argv and path
        sys.argv = old_argv
        sys.path[0] = old_path0
