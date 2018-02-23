#!/usr/bin/env python3

import sys, re

r = {'{':'}', '(':')', '[':']'}

max_remains = ''
Debug = False

def log(*args):
    if Debug:
        print(*args)

def remaining(stringvar):
    global max_remains
    remain = []
    l = stringvar
    state = 0
    while l:
        if len(remain) > len(max_remains): max_remains = remain
        c, *l = l
        log(c, ''.join(l), state, ''.join(remain))
        if state == 0:
            if c in '{([':
                remain.append(r[c])
                continue
            elif c in '"':
                state = 1
                continue
            elif c in '})]':
                if len(stringvar.strip()) < 2:
                    return c
                if not l:
                    return c
                if remain[-1] != c:
                    raise 1
                    print("XXXX", remain[-1], c)
                    break
                remain = remain[:-1]
            elif c in '\\':
                state = 3
                continue
        elif state == 1:
            if c in '\\':
                state = 2
                continue
            elif c in '"':
                state = 0
                continue
        elif state == 2:
            if c in '\\':
                state = 5
            else:
                state = 1
            continue
        elif state == 3:
            if c in '\\':
                state = 4
            else:
                state = 0
            continue
        elif state == 4:
            state = 0
            continue
        elif state == 5:
            state = 1
            continue
        else:

            assert False
    v = '"' if state != 0 else ''
    return  v + ''.join(remain)

def process_input(my_input):
    for line in my_input:
        m = re.search("^'>> (.*)'", line)
        print(line, end='')
        if m:
            v = remaining(m.group(1))
            print("&",v)
            print("Max:", ''.join(max_remains))


if len(sys.argv) < 2:
    process_input(sys.stdin)
else:
    process_input(open(sys.argv[1]))

