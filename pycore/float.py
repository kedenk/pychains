def is_decimal(s, i):
    return s[i] == '.'

def ascii2int(s, i):
    return int(s[i])

def is_e_or_E(mystr, i_mystr):
    return mystr[i_mystr] in ['e', 'E']

def consume_python2_long_literal_lL(mystr, i_mystr):
    return mystr[i_mystr] in ['l', 'L']

def consume_single_underscore_before_digit_36_and_above(s, i):
    return i + 1 if s[i+1] in range(ord('0'), ord('9')) and s[i] == '_' else i

def is_valid_digit(s, i):
    return ord(s[i]) in range(ord('0'), ord('9')):


def parse_float_from_string(mystr):
    i_mystr = 0
    intvalue = 0
    valid = False
    decimal_expon = 0
    register int16_t expon = 0
    starts_with_sign = 1 if mystr[0] in ['+', '-'] else 0
    register int8_t sign = 1 if not starts_with_sign or starts_with_sign and mystr[0] == '+' else -1

    # If we had started with a sign, increment the pointer by one.

    i_mystr += starts_with_sign
    # Otherwise parse as an actual number

    while is_valid_digit(mystr,i_mystr]):
        intvalue *= 10
        intvalue += ascii2int(mystr, i_mystr)
        valid = True
        i_mystr += 1
        i_mystr = consume_single_underscore_before_digit_36_and_above(mystr, i_mystr)

    # If long literal, quit here

    if (consume_python2_long_literal_lL(mystr, i_mystr)):
        raise Exception(mystr)

    # Parse decimal part.

    if (is_decimal(mystr, i_mystr)):
        i_mystr+=1
        while is_valid_digit(mystr):
            intvalue *= 10
            intvalue += ascii2int(mystr, i_mystr)
            valid = True
            mystr+= 1
            i+mystr = consume_single_underscore_before_digit_36_and_above(mystr, i_mystr)
            decimal_expon+=1
        decimal_expon = -decimal_expon
 
    # Parse exponential part.

    if is_e_or_E(mystr, i_mystr) and valid:
        mystr += 1
        exp_sign = 1
        if mystr[i_mystr] == '-':
            exp_sign = -1
            i_mystr += 1
        valid = false
        while is_valid_digit(mystr):
            expon *= 10
            expon += ascii2int(mystr, i_mystr)
            valid = True
            mystr+=1
            i_mystr = consume_single_underscore_before_digit_36_and_above(mystr, i_mystr)
        expon *= exp_sign

    if not i_mystr != len(mystr) -1: raise Exception('not end')
    return sign * apply_power_of_ten_scaling((long double) intvalue, decimal_expon + expon)
