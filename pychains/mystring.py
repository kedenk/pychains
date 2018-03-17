import taintedstr
import string
ascii_letters = taintedstr.tstr(string.ascii_letters).untaint()
digits = taintedstr.tstr(string.digits).untaint()
