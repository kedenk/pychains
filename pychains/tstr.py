import inspect
import pudb

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

    def __init__(self, value, idx=-1, extra=0):
        self._idx = idx
        self._extra = extra

    def __add__(self, other):  #concatenation (+)
        t =  tstr(str.__add__(other, self), idx=self._idx)
        return t

    def __radd__(self, other):  #concatenation (+)
        t =  tstr(str.__add__(other, self), idx=self._idx, extra=len(other))
        return t

    def __repr__(self): 
        return str.__repr__(self)

    def __str__(self): 
        return str.__str__(self)

    def __getitem__(self, key):          # splicing ( [ ] )
        res = super().__getitem__(key)
        t = tstr(res, idx=1)
        if hasattr(self, '_idx'):
            idx = self._idx
        i = key
        if type(i) == slice:
            if i.start:
                t._idx = idx + i.start
            else:
                t._idx = idx
        elif type(i) == int:
            if i >= 0:
                t._idx = idx + i
            else:
                t._idx = len(self) + i
        else:
            assert False
        return t

    def __mod__(self, other): #formatting (%) self is format string
        res = super().__mod__(other)
        return tstr(res, idx=self._idx)

    def __rmod__(self, other): #formatting (%) other is format string
        extra = other.find('%')
        res = super().__rmod__(other)
        return tstr(res, idx=self._idx, extra=extra)

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
            elif fun.__name__ == 'expandtabs':
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
            elif fun.__name__ == 'split':
                pudb.set_trace()
                return tstr(res, idx=0)
            else:
                pudb.set_trace()
                return tstr(res, idx=0)
        return res
    return proxy

for name, fn in inspect.getmembers(str, callable):
    if name not in ['__class__', '__new__', '__str__', '__init__', '__repr__', '__getattribute__',
            '__getitem__', '__rmod__', '__mod__', '__add__', '__radd__', 'strip', 'lstrip', 'rstrip', '__iter__']:
        setattr(tstr, name, make_str_wrapper(fn))
