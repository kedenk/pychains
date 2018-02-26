import inspect
import enum

class Op(enum.Enum):
    LT = 0
    LE = enum.auto()
    EQ = enum.auto()
    NE = enum.auto()
    GT = enum.auto()
    GE = enum.auto()
    IN = enum.auto()
    NOT_IN = enum.auto()
    IS = enum.auto()
    IS_NOT = enum.auto()
    ISSUBCLASS = enum.auto()
    FIND_STR = enum.auto()
    SPLIT_STR = enum.auto()

COMPARE_OPERATORS = {
        Op.EQ: lambda x, y: x == y,
        Op.NE: lambda x, y: x != y,
        Op.IN: lambda x, y: x in y,
        Op.NOT_IN: lambda x, y: x not in y
        }

class Instr:
    def __init__(self,o, a, b):
        self.opA = a
        self.opB = b
        self.op = o

    def o(self):
        if self.op == Op.EQ:
            return 'eq'
        elif self.op == Op.NE:
            return 'ne'
        else:
            return '?'

    def __repr__(self):
        return "(%s %s %s)" % (self.o(), repr(self.opA), repr(self.opB))

    def __str__(self):
        if self.op == Op.EQ:
            if str(self.opA) == str(self.opB):
                return "%s = %s" % (repr(self.opA), repr(self.opB))
            else:
                return "%s != %s" %  (repr(self.opA), repr(self.opB))
        elif self.op == Op.NE:
            if str(self.opA) == str(self.opB):
                return "%s = %s" %  (repr(self.opA), repr(self.opB))
            else:
                return "%s != %s" %  (repr(self.opA), repr(self.opB))
        elif self.op == Op.IN:
            if str(self.opA) in str(self.opB):
                return "%s in %s" % (repr(self.opA), repr(self.opB))
            else:
                return "%s not in %s" %  (repr(self.opA), repr(self.opB))
        elif self.op == Op.NOT_IN:
            if str(self.opA) in str(self.opB):
                return "%s in %s" % (repr(self.opA), repr(self.opB))
            else:
                return "%s not in %s" %  (repr(self.opA), repr(self.opB))
        else:
            assert False

Comparisons = []
class tstr_iterator():
    def __init__(self, tstr):
        self._tstr = tstr
        self._str_idx = 0

    def __next__(self):
        if self._str_idx == len(self._tstr): raise StopIteration
        # calls tstr getitem should be tstr
        c = self._tstr[self._str_idx]
        assert type(c) is tstr
        self._str_idx += 1
        return c


class tstr(str):
    def __new__(cls, value, *args, **kw):
        return super(tstr, cls).__new__(cls, value)

    def __init__(self, value, idx=-1, unmapped_till=0):
        self._idx = idx
        self._unmapped_till = unmapped_till

    def x(self, i=0):
        v = self.get_mapped_char_idx(i)
        if v < 0:
            raise Exception('Invalid mapped char idx in tstr')
        return v

    def split(self, sep = None, maxsplit = -1):
        splitted = super().split(sep, maxsplit)
        result_list = []
        index_counter = 0
        sep_len = len(sep) if sep else 0
        for i,s in enumerate(splitted):
            idx = self._idx + abs(min(0, self._unmapped_till - index_counter))
            unmapped = max(0, self._unmapped_till - index_counter)
            result_list.append(tstr(s, idx, unmapped))
            if not sep and len(splitted) > i+1:
                nxt = splitted[i+1]
                fr = index_counter + len(s)
                rest= super().__getitem__(slice(fr, None, None))
                sep_len = rest.find(nxt)
            index_counter += len(s) + sep_len
        Comparisons.append(Instr(Op.SPLIT_STR, self, sep))
        return result_list


    def find(self, sub, start=None, end=None):
        Comparisons.append(Instr(Op.FIND_STR, self, sub))
        return super().find(sub, start, end)


    # tpos is the index in the input string that we are
    # looking to see if contained in this string.
    def is_tpos_contained(self, tpos):
        tainted_len = len(self) - self._unmapped_till
        if self._idx <= tpos < self._idx + tainted_len: return True
        return False

    # idx is the string index of current string.
    def is_idx_tainted(self, idx):
        if idx < self._unmapped_till: return False
        if idx > len(self): return False
        return True

    def get_mapped_char_idx(self, i):
        # if the current string is not mapped to input till
        # char 10 (_unmapped_till), but the
        # character 10 is mapped to character 5 (_idx)
        # then requesting 10 should return 5
        #   which is 5 - 10 + 10
        # and requesting 11 should return 6
        #   which is 5 - 10 + 11
        return self._idx - self._unmapped_till + i

    # returns the index of the character this substring maps to
    # e.g. "start" is the original string, "art" is the current string, then "art".get_first_mapped_char() returns 2
    def get_first_mapped_char(self):
        return self._idx

    def __add__(self, other):  #concatenation (+)
        t =  tstr(str.__add__(self, other), idx=self._idx, unmapped_till=self._unmapped_till)
        return t

    def __radd__(self, other):  #concatenation (+) -- other is not tstr
        t =  tstr(str.__add__(other, self), idx=self._idx, unmapped_till=len(other)+self._unmapped_till)
        return t

    def __repr__(self):
        return str.__repr__(self) # + ':' + str((self._idx, self._unmapped_till))

    def __str__(self):
        return str.__str__(self)

    def __getitem__(self, key):          # splicing ( [ ] )
        res = super().__getitem__(key)
        t = tstr(res, idx=0)
        if type(key) == slice:
            t._idx = self.get_mapped_char_idx(key.start if key.start else 0)
        elif type(key) == int:
            if key >= 0:
                t._idx =  self.get_mapped_char_idx(key)
            else:
                # TODO: verify how unmapped_till should be added here.
                assert self._unmapped_till == 0
                t._idx = len(self) + key
        else:
            assert False
        return t

    def __mod__(self, other): #formatting (%) self is format string
        res = super().__mod__(other)
        return tstr(res, idx=self._idx)

    def __rmod__(self, other): #formatting (%) other is format string
        unmapped_till = other.find('%')
        res = super().__rmod__(other)
        return tstr(res, idx=self._idx, unmapped_till=unmapped_till)

    def strip(self, cl=None):
        res = super().strip(cl)
        i = self.find(res)
        return tstr(res, idx=i+self._idx)

    def lstrip(self, cl=None):
        res = super().lstrip(cl)
        i = self.find(res)
        return tstr(res, idx=i+self._idx)

    def rstrip(self, cl=None):
        res = super().rstrip(cl)
        return tstr(res, idx=self._idx)

    def capitalize(self):
        res = super().capitalize()
        return tstr(res, idx=self._idx)

    def __iter__(self):
        return tstr_iterator(self)

    def expandtabs(self):
        res = super().expandtabs()
        return tstr(res, idx=self._idx)

    def __format__(self, formatspec):
        res = super().__format__(formatspec)
        unmapped_till = res.find(self)
        return tstr(res, idx=self._idx, unmapped_till=unmapped_till)

    def __eq__(self, other):
        global Comparisons
        Comparisons.append(Instr(Op.EQ, self, other))
        return super().__eq__(other)

    def __ne__(self, other):
        global Comparisons
        Comparisons.append(Instr(Op.NE, self, other))
        return super().__ne__(other)

    def __contains__(self, other):
        global Comparisons
        Comparisons.append(Instr(Op.IN, other, self))
        return super().__contains__(other)

import pudb
def make_str_wrapper(fun):
    def proxy(*args, **kwargs):
        res = fun(*args, **kwargs)

        if fun.__name__ in ['capitalize', 'lower', 'upper', 'swapcase']:
            return tstr(res, idx=args[0]._idx)

        if res.__class__ == str:
            if fun.__name__ == '__mul__': #repeating (*)
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == '__rmul__': #repeating (*)
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'ljust':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'splitlines':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'center':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'rjust':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'zfill':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'format':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'rpartition':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'decode':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'partition':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'rsplit':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'encode':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'replace':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'title':
                pudb.set_trace()
                return tstr(res, idx=0)
            elif fun.__name__ == 'join':
                pudb.set_trace()
                return tstr(res, idx=0)
            else:
                pudb.set_trace()
                raise Exception('%s Not implemented in TSTR' % fun.__name__)
        return res
    return proxy

for name, fn in inspect.getmembers(str, callable):
    if name not in ['__class__', '__new__', '__str__', '__init__', '__repr__',
            '__getattribute__', '__getitem__', '__rmod__', '__mod__', '__add__',
            '__radd__', 'strip', 'lstrip', 'rstrip', '__iter__', 'expandtabs',
            '__format__', 'split', 'find', '__eq__', '__ne__', '__contains__']:
        setattr(tstr, name, make_str_wrapper(fn))

class mstr:
    def __init__(self, t):
        if type(t) is tstr:
            self.t = t
            self.s = str(t)
            self._idx = t._idx
            self._unmapped_till = t._unmapped_till
        else:
            self.s = t
            self.t = None
            self._idx = None
            self._unmapped_till = None
    def __repr__(self): return self.s
    def __str__(self): return self.s
