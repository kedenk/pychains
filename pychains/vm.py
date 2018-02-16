import bytevm.pyvm2 as pvm
import enum


def brk(v=True):
    if not v: return None
    import pudb
    pudb.set_trace()

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

class TraceOp:
    def __init__(self, opnum, oargs, lineinfo):
        self.__dict__.update(locals())
        del self.__dict__['self']
        self.opA, self.opB = oargs
        self._r = None

    def to_loc(self):
        return "%s:%s %s" % self.lineinfo

    def __repr__(self):
        if not self._r:
            self.result = pvm.VirtualMachine.COMPARE_OPERATORS[self.opnum](self.opA, self.opB)
            self._r = "%s %s %s %s" % (Op(self.opnum).name, self.oargs, self.result, self.to_loc())
        return self._r

class TrackerVM(pvm.VirtualMachine):
    def __init__(self):
        self.cmp_trace = []
        self.cmp_trace = []
        self.byte_trace = []
        super().__init__()

    def byte_COMPARE_OP(self, opnum):
        # Get the comparions. The filtering can be done later if needed.
        opA, opB = self.frame.stack[-2:]
        self.cmp_trace.append(TraceOp(opnum, [opA, opB], (self.fn, self.line, self.cn)))
        super().byte_COMPARE_OP(opnum)

    def byte_LOAD_ATTR(self, name):
        super().byte_LOAD_ATTR(name)

    def byte_LOAD_GLOBAL(self, name):
        super().byte_LOAD_GLOBAL(name)

    def byte_LOAD_NAME(self, name):
        if name == 'brk':
            brk()
            return
        super().byte_LOAD_NAME(name)

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

    def call_function(self, arg, args, kwargs):
        return super().call_function(arg, args, kwargs)

    def parse_byte_and_args(self):
        byteName, arguments, offset = super().parse_byte_and_args()
        self.byte_trace.append((byteName, arguments, self.frame.stack))
        return (byteName, arguments, offset)


    def get_trace(self):
        return self.cmp_trace
