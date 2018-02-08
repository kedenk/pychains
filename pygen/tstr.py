import inspect

class tstr(str):
    def __new__(cls, value, *args, **kw):
        return super(tstr, cls).__new__(cls, value)

    def __init__(self, value, idx=-1):
        self._idx = idx

    def __radd__(self, other): 
        t =  tstr(str.__add__(other, self), idx=0)
        return t

    def __repr__(self): 
        return str.__repr__(self)
    def __str__(self): 
        return str.__str__(self)

def make_str_wrapper(fun):
    def proxy(*args, **kwargs):
        res = fun(*args, **kwargs)

        if res.__class__ == str:
            if fun.__name__ == '__getitem__':
                t = tstr(res, idx=1)
                if hasattr(args[0], '_idx'):
                    idx = args[0]._idx
                i = args[1]
                if type(i) == slice:
                    if i.start:
                        t._idx = idx + i.start
                    else:
                        t._idx = idx
                elif type(i) == int:
                    if i >= 0:
                        t._idx = idx + i
                    else:
                        t._idx = len(t) + i
                else:
                    assert False
                return t
            elif fun.__name__ == '__rmod__':
                return tstr(res, idx=0)
            else:
                assert False
        return res
    return proxy

for name, fn in inspect.getmembers(str, callable):
    if name not in ['__class__', '__new__', '__str__', '__init__', '__repr__']:
        setattr(tstr, name, make_str_wrapper(fn))
