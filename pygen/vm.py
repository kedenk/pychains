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

class TrackerVM(pvm.VirtualMachine):
    def __init__(self):
        self.trace = []
        super().__init__()

    def byte_COMPARE_OP(self, opnum):
        # Get the comparions. The filtering can be done later if needed.
        opA, opB = self.frame.stack[-2:]
        result = self.COMPARE_OPERATORS[opnum](opA, opB)
        self.trace.append((Op(opnum), [opA, opB], result, (self.line, self.fn, self.cn)))
        super().byte_COMPARE_OP(opnum)

    def get_trace(self):
        return self.trace
