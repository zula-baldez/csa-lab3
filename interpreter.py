import re
from enum import Enum

from isa import Opcode
from isa import instruction_to_json


# LEXER--------------------------------

class Token(Enum):
    IF = r'if'
    WHILE = r'while'
    READ = r'read'
    PRINT = r'print'
    LET = r'let'
    EQ = r'=='
    GE = r'>='
    GT = r'>'
    LT = r'<'
    LE = r'<='
    NEQ = r'!='
    PLUS = r'\+'
    MINUS = r'-'
    MUL = r'\*'
    DIV = r'/'
    LPAREN = r'\('
    RPAREN = r'\)'
    LBRACE = r'{'
    RBRACE = r'}'
    SEMICOLON = r';'
    ASSIGN = r'='
    INCREMENT = r'\+\+'
    DECREMENT = r'--'
    NAME = r'[a-zA-Z]+'
    STRING = r'"[a-zA-Z]+"'
    NUMBER = r'-?[0-9]+'


class AstType(Enum):
    IF = 'if'
    WHILE = 'while'
    READ = 'read'
    PRINT = 'print'
    LET = 'let'
    EQ = 'eq'
    GE = 'ge'
    GT = 'gt'
    LT = 'lt'
    LE = 'ne'
    NEQ = 'neq'
    PLUS = 'plus'
    MINUS = 'minus'
    MUL = 'mul'
    DIV = 'div'
    STRING = 'string'
    NUMBER = 'number'
    NAME = 'name'
    ROOT = 'root'
    BLOCK = 'block'
    ASSIGN = 'assign'
    CMP = 'cmp'


type2opcode = {
    AstType.EQ: Opcode.JE,
    AstType.GE: Opcode.JGE,
    AstType.GT: Opcode.JG,
    AstType.LT: Opcode.JL,
    AstType.LE: Opcode.JLE,
    AstType.NEQ: Opcode.JNE,
    AstType.PLUS: Opcode.ADD,
    AstType.MINUS: Opcode.SUB,
    AstType.MUL: Opcode.MUL,
    AstType.DIV: Opcode.DIV,
    AstType.PRINT: Opcode.PRINT,
    AstType.READ: Opcode.INPUT,
}

token_to_type: dict[Token, AstType] = {
    Token.IF: AstType.IF,
    Token.WHILE: AstType.WHILE,
    Token.READ: AstType.READ,
    Token.PRINT: AstType.PRINT,
    Token.LET: AstType.LET,
    Token.EQ: AstType.EQ,
    Token.GE: AstType.GE,
    Token.GT: AstType.GT,
    Token.LT: AstType.LT,
    Token.LE: AstType.LE,
    Token.NEQ: AstType.NEQ,
    Token.PLUS: AstType.PLUS,
    Token.MINUS: AstType.MINUS,
    Token.MUL: AstType.MUL,
    Token.DIV: AstType.DIV,
    Token.STRING: AstType.STRING,
    Token.NUMBER: AstType.NUMBER,
    Token.NAME: AstType.NAME,
    Token.ASSIGN: AstType.ASSIGN,
}


def map_token_to_type(token: Token) -> AstType:
    if token_to_type.get(token) is None:
        raise Exception('Invalid token {}'.format(token.name))
    return token_to_type.get(token)


def lex(program: str) -> list[tuple[Token, str]]:
    regex = '|'.join(f'(?P<{t.name}>{t.value})' for t in Token)
    found_tokens = re.finditer(regex, program)
    tokens: list[tuple[Token, str]] = []
    for token in found_tokens:
        t_type = token.lastgroup
        t_value = token.group(t_type)
        if t_type != 'WS':
            tokens.append((Token[t_type], t_value))
    return tokens


# PARSER-------------------

class AstNode:
    def __init__(self, ast_type: AstType, value=""):
        self.astType = ast_type
        self.children: list[AstNode] = []
        self.value = value

    @classmethod
    def from_token(cls, token: Token, value="") -> 'AstNode':
        return cls(map_token_to_type(token), value)

    def add_child(self, node: 'AstNode') -> None:
        self.children.append(node)


# PARSE MATH EXPRESSION -------------
def match_list(tokens: list[tuple[Token, str]], token_req: list[Token]):
    if tokens[0][0] in token_req:
        return
    else:
        raise Exception('Invalid syntax on token {}'.format(tokens[0][0].name))


def match_list_and_delete(tokens: list[tuple[Token, str]], token_req: list[Token]) -> tuple[Token, str]:
    if tokens[0][0] in token_req:
        return tokens.pop(0)
    else:
        raise Exception('Invalid syntax on token {}'.format(tokens[0][0].name))


def get_token_value(token: Token, value: str) -> str | int:
    if token == Token.STRING or token == Token.NAME:
        return value
    elif token == Token.NUMBER:
        return int(value)
    else:
        raise Exception('Invalid literal type {}'.format(token))


def parse_math_expression(tokens: list[tuple[Token, str]]) -> AstNode:
    return parse_first_level_operation(tokens)


# to save priority of operations
def parse_first_level_operation(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_second_level_operations(tokens)
    node: AstNode = left_node

    while tokens and tokens[0][0] in [Token.PLUS, Token.MINUS]:
        node = AstNode.from_token(tokens[0][0])
        tokens.pop(0)
        node.add_child(left_node)
        node.add_child(parse_second_level_operations(tokens))
        left_node = node
    return node


def parse_second_level_operations(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_literal_or_name(tokens)
    node: AstNode = left_node

    while tokens and tokens[0][0] in [Token.MUL, Token.DIV]:
        node = AstNode.from_token(tokens[0][0])
        tokens.pop(0)
        node.add_child(left_node)
        node.add_child(parse_literal_or_name(tokens))
        left_node = node
    return node


def parse_literal_or_name(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.NAME or tokens[0][0] == Token.NUMBER:
        # todo check type of variable
        node: AstNode = AstNode.from_token(tokens[0][0], get_token_value(tokens[0][0], tokens[0][1]))
        tokens.pop(0)
        return node
    match_list_and_delete(tokens, [Token.LPAREN])
    expression: AstNode = parse_first_level_operation(tokens)
    match_list_and_delete(tokens, [Token.RPAREN])
    return expression


# PARSE COMPARISON ----------------


# Math operation or str. Type checking is on the ast to machine instruction translation phase
def parse_operand(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.STRING:
        node: AstNode = AstNode.from_token(tokens[0][0], get_token_value(tokens[0][0], tokens[0][1]))
        tokens.pop(0)
        return node
    else:
        node: AstNode = parse_math_expression(tokens)
    return node


def parse_comparison(tokens: list[tuple[Token, str]]) -> AstNode:
    left_node: AstNode = parse_math_expression(tokens)
    match_list(tokens, [Token.GE, Token.GT, Token.LE, Token.LT, Token.NEQ, Token.EQ])
    comp: AstNode = AstNode.from_token(tokens[0][0])
    tokens.pop(0)
    right_node: AstNode = parse_math_expression(tokens)
    comp.add_child(left_node)
    comp.add_child(right_node)
    return comp


def parse_if(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.IF)
    match_list_and_delete(tokens, [Token.IF])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_comparison(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    node.add_child(parse_block(tokens))
    return node


def parse_while(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.WHILE)
    match_list_and_delete(tokens, [Token.WHILE])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_comparison(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    node.add_child(parse_block(tokens))
    return node


def parse_allocation(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.LET)
    match_list_and_delete(tokens, [Token.LET])
    node.add_child(AstNode.from_token(Token.NAME, tokens[0][1]))
    tokens.pop(0)
    match_list_and_delete(tokens, [Token.ASSIGN])
    node.add_child(parse_operand(tokens))
    match_list_and_delete(tokens, [Token.SEMICOLON])
    return node


def parse_assignment(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.ASSIGN)
    match_list(tokens, [Token.NAME])
    node.add_child(AstNode.from_token(Token.NAME, tokens[0][1]))
    tokens.pop(0)
    match_list_and_delete(tokens, [Token.ASSIGN])
    node.add_child(parse_operand(tokens))
    match_list_and_delete(tokens, [Token.SEMICOLON])
    return node


def parse_print(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.PRINT)
    match_list_and_delete(tokens, [Token.PRINT])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_operand(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    return node


def parse_read(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.READ)
    match_list_and_delete(tokens, [Token.READ])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(AstNode.from_token(Token.NAME, tokens[0][1]))
    tokens.pop(0)
    match_list_and_delete(tokens, [Token.RPAREN])
    return node


def parse_statement(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.IF:
        return parse_if(tokens)
    elif tokens[0][0] == Token.WHILE:
        return parse_while(tokens)
    elif tokens[0][0] == Token.LET:
        return parse_allocation(tokens)
    elif tokens[0][0] == Token.PRINT:
        return parse_print(tokens)
    elif tokens[0][0] == Token.READ:
        return parse_read(tokens)
    elif tokens[0][0] == Token.NAME:
        return parse_assignment(tokens)
    else:
        raise Exception('Invalid statement {}'.format(tokens[0][0].name))


def parse_block(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode(AstType.BLOCK)
    match_list_and_delete(tokens, [Token.LBRACE])
    while tokens[0][0] != Token.RBRACE:
        node.add_child(parse_statement(tokens))
    match_list_and_delete(tokens, [Token.RBRACE])
    return node


def parse_program(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode(AstType.ROOT)
    while tokens:
        node.add_child(parse_statement(tokens))
    return node


def parse(program: str) -> AstNode:
    return parse_program(lex(program))


# AST TO MACHINE INSTRUCTION TRANSLATION ----------------

# all memory is static
# all variables are stored in memory
# the program begins on address 0
# the static memory is after the program
# in the end, the stack is placed
# the address of memory of the variable is unknown because memory is placed after program and program size is ubknown
# so in the end add size of program to every address of variable


class Program:
    def __init__(self):
        self.machine_code: list[dict[str, int | str | list[int | str]]] = []
        self.current_address = 0
        self.current_offset = 0
        self.variables: dict[str, int] = {}
        self.static_mem: list[str | int] = []
        self.reg_to_var: dict[str, str] = {}
        self.var_to_reg: dict[str, str] = {}
        self.reg_counter = 0

    def add_instruction(self, opcode: Opcode, arg: list[int | str] | (int | str) = '') -> int:
        self.machine_code.append(instruction_to_json(opcode, self.current_address, arg))
        self.current_address += 1
        return self.current_address - 1

    def preserve_place(self, size: int) -> int:
        self.current_address += size
        return self.current_address - size

    def add_variable_in_static_mem(self, name: str, size: int, value: int | str) -> int:
        self.variables[name] = self.current_offset
        self.current_offset += size
        self.static_mem.append(value)
        return self.current_offset - size

    def get_variable_offset(self, name: str) -> int:
        return self.variables[name]

    def update_var_value(self, name: str, value: int | str) -> None:
        self.static_mem[self.variables[name]] = value

    def resolve_static_mem(self) -> None:
        for instruction in self.machine_code:
            if instruction['opcode'] == Opcode.LD.value:
                instruction['arg'][1] += self.current_offset
        for name in self.variables:
            self.machine_code.append({
                'index': self.current_address, 'opcode': 'JUMP', 'arg': self.variables[name]
            })
            self.current_address += 1  # todo len of variable

    def change_data_reg(self) -> str:
        self.reg_counter += 1
        if self.reg_counter > 10:
            self.reg_counter = 0
        return 'r' + str(self.reg_counter)

    def get_var_reg(self, var_name: str) -> str:
        reg = self.var_to_reg[var_name]
        if reg is not None:
            return reg
        else:
            return self.change_data_reg()

    def load_literal(self) -> str:
        reg = self.change_data_reg()
        var: str | None = self.reg_to_var.get(reg)
        self.reg_to_var.pop(reg, None)
        self.var_to_reg.pop(var, None)
        return reg


def ast_to_machine_code(root: AstNode) -> list[dict[str, int | str]]:
    program = Program()
    for child in root.children:
        ast_to_machine_code_rec(child, program)
    program.resolve_static_mem()
    return program.machine_code


def ast_to_machine_code_rec(node: AstNode, program: Program) -> None:
    if node.astType == AstType.IF:
        ast_to_machine_code_if(node, program)
    elif node.astType == AstType.WHILE:
        (ast_to_machine_code_while(node, program))
    elif node.astType == AstType.LET or node.astType == AstType.ASSIGN:
        (ast_to_machine_code_let(node, program))
    elif node.astType == AstType.PRINT or node.astType == AstType.READ:
        (ast_to_machine_code_read_print(node, program))
    else:
        raise Exception('Invalid ast node type {}'.format(node.astType.name))


# правый операнд всегда в r10 лежит)
def ast_to_machine_code_math(node: AstNode, program: Program, is_right: bool) -> None:
    if node.astType == AstType.NUMBER:
        reg = program.load_literal()
        program.add_instruction(Opcode.LD_LIT, [reg, node.value])
        if not is_right:
            program.add_instruction(Opcode.MV, [reg, 'r11'])
        else:
            program.add_instruction(Opcode.MV, [reg, 'r12'])
        return
    if node.astType == AstType.NAME:
        var_offs = program.get_variable_offset(node.value)
        reg = program.get_var_reg(node.value)
        program.add_instruction(Opcode.LD, [reg, var_offs])  # todo load only if variable not found in register
        if not is_right:
            program.add_instruction(Opcode.MV, [reg, 'r11'])
        else:
            program.add_instruction(Opcode.MV, [reg, 'r12'])
        return
    ast_to_machine_code_math(node.children[0], program, False)
    ast_to_machine_code_math(node.children[1], program, True)
    if is_right:
        program.add_instruction(type2opcode[node.astType], ['r11', 'r12', 'r11'])
    else:
        program.add_instruction(type2opcode[node.astType], ['r10', 'r11', 'r10'])


def ast_to_machine_code_block(node: AstNode, program: Program) -> int:
    for child in node.children:
        ast_to_machine_code_rec(child, program)
    return program.current_address


def ast_to_machine_code_if(node: AstNode, program: Program) -> None:
    comp = node.children[0]
    addr_left = parse_expression(comp.children[0], program)
    addr_right = parse_expression(comp.children[1], program)
    if addr_left is not None:
        program.add_instruction(Opcode.LD, ['r1', addr_left])  # todo string
    else:
        program.add_instruction(Opcode.POP, 'r1')
    if addr_right is not None:
        program.add_instruction(Opcode.LD, ['r2', addr_right])  # todo string
    else:
        program.add_instruction(Opcode.POP, 'r2')
    program.add_instruction(Opcode.CMP, ['r1', 'r2'])
    comp_addr = program.add_instruction(type2opcode[comp.astType], ['r1', -1])
    block_end: int = ast_to_machine_code_block(node.children[1], program)

    program.machine_code[comp_addr]['arg'] = ['r1', block_end + 1]


def ast_to_machine_code_while(node: AstNode, program: Program) -> None:
    comp = node.children[0]
    while_begin: int = program.current_address
    addr_left = parse_expression(comp.children[0], program)
    if addr_left is None:
        program.add_instruction(Opcode.MV, ['r10', 'r13'])
    else:
        program.add_instruction(Opcode.LD, ['r13', addr_left])
    addr_right = parse_expression(comp.children[1], program)
    if addr_right is not None:
        program.add_instruction(Opcode.LD, ['r10', addr_right])  # todo string
    program.add_instruction(Opcode.CMP, ['r13', 'r10'])
    cmp_reg = program.load_literal()  # todo другое название, тут фактически для резевирования регистра
    comp_addr = program.add_instruction(type2opcode[comp.astType], [cmp_reg, -1])  # тож можно убрать
    block_end: int = ast_to_machine_code_block(node.children[1], program)
    program.add_instruction(Opcode.JUMP, while_begin)

    program.machine_code[comp_addr]['arg'] = [cmp_reg, block_end + 1]


def ast_to_machine_code_let(node: AstNode,
                            program: Program) -> None:  # no instruction added, only variables in static memory
    if node.astType == AstType.LET:
        name = node.children[0].value  # todo math calculations
        size = 4 if node.children[1].astType == AstType.NUMBER else len(
            node.children[1].value) + 1  # todo pascal string
        program.add_variable_in_static_mem(name, size, node.children[1].value)
    else:
        program.update_var_value(node.children[0].value, node.children[1].value)


def ast_to_machine_code_read_print(node: AstNode, program: Program) -> None:
    parse_expression(node.children[0], program)
    program.add_instruction(type2opcode[node.astType], ['r11'])


def parse_expression(node: AstNode, program: Program) -> int | None:
    if node.astType == AstType.NAME:
        var_offs = program.get_variable_offset(node.value)
        # program.add_instruction(Opcode.LD, ['r1', var_offs])
        return var_offs
    if node.astType == AstType.STRING:  # TODO check if string is in static memory
        addr = program.add_variable_in_static_mem(node.value, len(node.value) + 1, node.value)
        # program.add_instruction(Opcode.LD, ['r1', addr]) #todo string
        return addr
    ast_to_machine_code_math(node, program, False)


# TEST --------------------

test = '''
    let x = 5;
    while(x > (10*10+20*20)) {
	x=x-2;
	print(x)
	x=x-123;
}
'''
tt = parse(test)
test = ast_to_machine_code(tt)
for t in test:
    print(t)
x = 123

# def __main__(args: list[str]) -> None:
#     assert len(args) == 2
#     input_file, output_file = args
#
