import sys
import bytevm.pyvm2 as pvm
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

class TraceOp:
    def __init__(self, opnum, oargs, result, lineinfo):
        self.__dict__.update(locals())
        self.opA, self.opB = oargs

    def to_loc(self):
        return "%s:%s %s" % self.lineinfo

    def __repr__(self):
        return "%s %s %s %s" % (Op(self.opnum).name, self.oargs, self.result, self.to_loc())

class TrackerVM(pvm.VirtualMachine):
    def __init__(self):
        self.cmp_trace = []
        self.cmp_trace = []
        self.byte_trace = []
        super().__init__()

    def byte_COMPARE_OP(self, opnum):
        # Get the comparions. The filtering can be done later if needed.
        opA, opB = self.frame.stack[-2:]
        result = self.COMPARE_OPERATORS[opnum](opA, opB)
        self.cmp_trace.append(TraceOp(opnum, [opA, opB], result, (self.fn, self.line, self.cn)))
        super().byte_COMPARE_OP(opnum)

    def parse_byte_and_args(self):
        byteName, arguments, offset = super().parse_byte_and_args()
        self.byte_trace.append((byteName, arguments, self.frame.stack))
        return (byteName, arguments, offset)


    def get_trace(self):
        return self.cmp_trace
