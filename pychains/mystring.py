import taintedstr
import datatypes.taintedbytes as tb
import string
ascii_letters = taintedstr.tstr(string.ascii_letters).untaint()
digits = taintedstr.tstr(string.digits).untaint()

hexdigits = tb.tbytes(string.hexdigits).untaint()
