import ast
from tainted import tstr

class TstrTransformer(ast.NodeTransformer):

    def __init__(self, string_literals):
        self.string_literals = string_literals

    # helper function to collect all string literals in the code, filter by certain constraints
    def add_string_literal(self, string_literal: str):
        string_literal = string_literal.replace("'", "").replace('"', '')
        if len(string_literal) > 1 and string_literal.isalpha():
            self.string_literals.add(string_literal)

    def visit_Str(self, node):
        tstr_call = ast.parse("tstr('abc')").body[0].value
        tstr_call.args = [node]
        self.add_string_literal(node.s)
        return tstr_call

    def visit_Call(self, node):
        return node
