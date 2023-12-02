import re
import sys
from enum import Enum

from isa import Opcode, Word, write_code


# LEXER--------------------------------

class Token(Enum):
    IF = r'if'
    WHILE = r'while'
    READ = r'read'
    PRINT_STR = r'print_str'
    PRINT_INT = r'print_int'
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
    NAME = r'[a-zA-Z0-9]+'
    STRING = r'"[0-9a-zA-Z\s]+"'
    NUMBER = r'-?[0-9]+'


def lex(program: str) -> list[tuple[Token, str]]:
    regex = '|'.join(f'(?P<{t.name}>{t.value})' for t in Token)
    found_tokens = re.finditer(regex, program)
    tokens: list[tuple[Token, str]] = []
    for token in found_tokens:
        t_type: str = token.lastgroup
        t_value: str = token.group(t_type)
        if t_type == 'STRING':
            tokens.append((Token[t_type], t_value[1:-1]))
        else:
            tokens.append((Token[t_type], t_value))
    return tokens


# PARSER-------------------


class AstType(Enum):
    IF = 'if'
    WHILE = 'while'
    READ = 'read'
    PRINT_STR = 'print_str'
    PRINT_INT = 'print_int'
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


token2type: dict[Token, AstType] = {
    Token.IF: AstType.IF,
    Token.WHILE: AstType.WHILE,
    Token.READ: AstType.READ,
    Token.PRINT_STR: AstType.PRINT_STR,
    Token.PRINT_INT: AstType.PRINT_INT,
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
    if token2type.get(token) is None:
        raise Exception('Invalid token {}'.format(token.name))
    return token2type.get(token)


class AstNode:
    def __init__(self, ast_type: AstType, value: str = ""):
        self.astType = ast_type
        self.children: list[AstNode] = []
        self.value = value

    @classmethod
    def from_token(cls, token: Token, value: str = "") -> 'AstNode':
        return cls(map_token_to_type(token), value)

    def add_child(self, node: 'AstNode') -> None:
        self.children.append(node)


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
        node: AstNode = AstNode.from_token(tokens[0][0], tokens[0][1])
        tokens.pop(0)
        return node
    match_list_and_delete(tokens, [Token.LPAREN])
    expression: AstNode = parse_first_level_operation(tokens)
    match_list_and_delete(tokens, [Token.RPAREN])
    return expression


# Math operation or str. Type checking is on the ast to machine instruction translation phase
def parse_operand(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.STRING:
        node: AstNode = AstNode.from_token(tokens[0][0], tokens[0][1])
        tokens.pop(0)
        return node
    elif tokens[0][0] == Token.READ:
        return parse_read(tokens)
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


def parse_if_or_while(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.IF, Token.WHILE])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_comparison(tokens))
    match_list_and_delete(tokens, [Token.RPAREN])
    node.add_child(parse_block(tokens))
    return node


def parse_allocation_or_assignment(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.LET:
        node: AstNode = AstNode.from_token(Token.LET)
        match_list_and_delete(tokens, [Token.LET])
    else:
        node: AstNode = AstNode.from_token(Token.ASSIGN)
    match_list(tokens, [Token.NAME])
    node.add_child(AstNode.from_token(Token.NAME, tokens[0][1]))
    tokens.pop(0)
    match_list_and_delete(tokens, [Token.ASSIGN])
    node.add_child(parse_operand(tokens))
    match_list_and_delete(tokens, [Token.SEMICOLON])
    return node


def parse_print(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(tokens[0][0])
    match_list_and_delete(tokens, [Token.PRINT_STR, Token.PRINT_INT])
    match_list_and_delete(tokens, [Token.LPAREN])
    node.add_child(parse_operand(tokens))
    if node.astType == AstType.PRINT_INT:  # мб проверку вынести в маппинг в машшиный код? все равно тип переменной непонятно как смотреть
        assert node.children[0].astType != AstType.STRING
    if node.astType == AstType.PRINT_STR:
        assert node.children[0].astType == AstType.STRING or node.children[0].astType == AstType.NAME
    match_list_and_delete(tokens, [Token.RPAREN])
    match_list_and_delete(tokens, [Token.SEMICOLON])

    return node


def parse_read(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode.from_token(Token.READ)
    match_list_and_delete(tokens, [Token.READ])
    match_list_and_delete(tokens, [Token.LPAREN])
    match_list_and_delete(tokens, [Token.RPAREN])
    return node


def parse_block(tokens: list[tuple[Token, str]]) -> AstNode:
    node: AstNode = AstNode(AstType.BLOCK)
    match_list_and_delete(tokens, [Token.LBRACE])
    while tokens[0][0] != Token.RBRACE:
        node.add_child(parse_statement(tokens))
    match_list_and_delete(tokens, [Token.RBRACE])
    return node


def parse_statement(tokens: list[tuple[Token, str]]) -> AstNode:
    if tokens[0][0] == Token.IF or tokens[0][0] == Token.WHILE:
        return parse_if_or_while(tokens)
    elif tokens[0][0] == Token.LET or tokens[0][0] == Token.NAME:
        return parse_allocation_or_assignment(tokens)
    elif tokens[0][0] == Token.PRINT_STR or tokens[0][0] == Token.PRINT_INT:
        return parse_print(tokens)
    elif tokens[0][0] == Token.READ:
        return parse_read(tokens)
    else:
        raise Exception('Invalid statement {}'.format(tokens[0][0].name))


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
    AstType.PRINT_INT: Opcode.PRINT_CHAR,
}

static_mem_label: str = 'static_mem_start'


condition_inverted = {
    Opcode.JE: Opcode.JNE,
    Opcode.JGE: Opcode.JL,
    Opcode.JG: Opcode.JLE,
    Opcode.JL: Opcode.JGE,
    Opcode.JLE: Opcode.JG,
    Opcode.JNE: Opcode.JE,
}


class VariableType(Enum):
    STRING = 'STRING',
    INT = 'INT',


# ld_op_to_var_type: dict[VariableType, str] = {
#     VariableType.STRING, LD
# }


class Program:
    def __init__(self):
        self.machine_code: list[Word] = []
        self.current_address = 0  # адрес последней команды, в 4байтовых байтах
        self.current_offset = 0  # оффсет следующей переменной от начала статической памяти
        self.variables: dict[str, int] = {}  # переменные и их адрес(оффсет на самом деле)
        # TODO хранить еще тип переменной???
        self.static_mem: list[int] = []  # статическая память побайтово, потом будет скопирована в machine code в самый
        # конец (когд оффсет узнаем)
        self.reg_to_var: dict[str, str] = {}
        self.var_to_reg: dict[str, str] = {}
        self.reg_counter = 1

    def add_instruction(self, opcode: Opcode, arg: list[int | str] = "") -> int:
        self.machine_code.append(Word(self.current_address, opcode, arg))
        self.current_address += 1
        return self.current_address - 1

    def add_data(self, value: int):
        self.static_mem.append(value)
        self.current_offset += 1

    def add_variable_in_static_mem(self, value: str, variable_type: VariableType) -> int:
        size = 1
        if variable_type == VariableType.STRING:
            size = len(value)
            #  str moment
            self.add_data(size)
            for char in value:
                self.add_data(ord(char))
            size += 1
        else:
            self.add_data(int(value))
        return self.current_offset - size

    def get_variable_offset(self, name: str) -> int | None:
        return self.variables.get(name)

    def resolve_static_mem(self) -> None:
        # reserving buffer for inp and output(32 bytes)
        static_mem_start = self.current_address
        for buf_offset in range(0, 32):
            self.add_instruction(Opcode.JUMP, [0])
        for instruction in self.machine_code:
            if len(instruction.arg) > 0 and instruction.arg[0] == static_mem_label:
                instruction.arg[0] = static_mem_start
            elif len(instruction.arg) > 1 and instruction.arg[1] == static_mem_label:
                instruction.arg[1] = static_mem_start
            elif instruction.opcode == Opcode.LD_ADDR or instruction.opcode == Opcode.ST_ADDR:
                instruction.arg[1] += self.current_address
        for data in self.static_mem:
            self.add_instruction(Opcode.JUMP, [data])

    def _change_reg(self) -> str:
        self.reg_counter += 1
        if self.reg_counter >= 9:
            self.reg_counter = 1
        return 'r' + str(self.reg_counter)

    def clear_register_for_variable(self) -> str:
        reg = self._change_reg()
        var: str | None = self.reg_to_var.get(reg)
        self.reg_to_var.pop(reg, None)
        self.var_to_reg.pop(var, None)
        return reg

    def load_variable(self, var_name: str) -> str:
        reg = self.var_to_reg.get(var_name)
        if reg is not None:
            return reg
        else:
            reg = self.clear_register_for_variable()
            var_offs = self.get_variable_offset(var_name)
            self.add_instruction(Opcode.LD_ADDR, [reg, var_offs])
            self.var_to_reg[var_name] = reg
            self.reg_to_var[reg] = var_name
            return reg

    def clear_variable_in_registers(self, name: str) -> None:
        reg: str | None = self.var_to_reg.get(name)
        if reg is not None:
            self.reg_to_var.pop(reg, None)
            self.var_to_reg.pop(name, None)

    def drop_variables_in_registers(self):
        self.reg_to_var.clear()
        self.var_to_reg.clear()

def ast_to_machine_code(root: AstNode) -> list[Word]:
    program = Program()
    for child in root.children:
        ast_to_machine_code_rec(child, program)
    program.add_instruction(Opcode.HALT)
    program.resolve_static_mem()
    return program.machine_code


def ast_to_machine_code_rec(node: AstNode, program: Program) -> None:
    if node.astType == AstType.WHILE or node.astType == AstType.IF:
        ast_to_machine_code_if_or_while(node, program)
    elif node.astType == AstType.LET:
        ast_to_machine_code_let(node, program)
    elif node.astType == AstType.ASSIGN:
        ast_to_machine_code_assign(node, program)
    elif node.astType == AstType.PRINT_STR or node.astType == AstType.PRINT_INT:
        (ast_to_machine_code_print(node, program))
    else:
        raise Exception('Invalid ast node type {}'.format(node.astType.name))


# TODO
# все остальное через стек
def ast_to_machine_code_math(node: AstNode, program: Program):
    ast_to_machine_code_math_rec(node, program)
    program.add_instruction(Opcode.POP, ['r9'])


def ast_to_machine_code_math_rec(node: AstNode, program: Program):
    if node.astType == AstType.NUMBER:
        program.add_instruction(Opcode.LD_LIT, ['r9', int(node.value)])
        program.add_instruction(Opcode.PUSH, ['r9'])
        return
    if node.astType == AstType.NAME:
        reg = program.load_variable(node.value)
        program.add_instruction(Opcode.MV, [reg, 'r9'])
        program.add_instruction(Opcode.PUSH, ['r9'])
        return
    ast_to_machine_code_math_rec(node.children[0], program)
    ast_to_machine_code_math_rec(node.children[1], program)

    program.add_instruction(Opcode.POP, ['r10'])
    program.add_instruction(Opcode.POP, ['r9'])
    program.add_instruction(type2opcode[node.astType], ['r9', 'r10'])
    program.add_instruction(Opcode.PUSH, ['r9'])


def ast_to_machine_code_block(node: AstNode, program: Program) -> int:
    for child in node.children:
        ast_to_machine_code_rec(child, program)
    return program.current_address


def ast_to_machine_code_if_or_while(node: AstNode, program: Program) -> None:
    program.drop_variables_in_registers()
    comp = node.children[0]
    block_begin: int = program.current_address
    addr_left = parse_expression(comp.children[0], program)
    if addr_left is None:
        program.add_instruction(Opcode.MV, ['r9', 'r12'])
    else:
        program.add_instruction(Opcode.LD_ADDR, ['r12', addr_left])
    addr_right = parse_expression(comp.children[1], program)
    if addr_right is not None:
        program.add_instruction(Opcode.LD_ADDR, ['r9', addr_right])

    program.add_instruction(Opcode.CMP, ['r12', 'r9'])
    comp_addr = program.add_instruction(condition_inverted[type2opcode[comp.astType]], [-1])
    block_end: int = ast_to_machine_code_block(node.children[1], program)
    if node.astType == AstType.WHILE:
        program.add_instruction(Opcode.JUMP, [block_begin])
    program.machine_code[comp_addr].arg = [block_end + 1]


# цикл ввода, захардкожен, так как все известно на этапе компиляции
def ast_to_machine_code_read(program: Program) -> None:
    program.add_instruction(Opcode.LD_LIT, ['r11', 0])  # счетчик
    program.add_instruction(Opcode.LD_LIT, ['r10', 0])  # to cmp
    program.add_instruction(Opcode.LD_LIT, ['r12', static_mem_label])
    do_while_start = program.current_address
    program.add_instruction(Opcode.READ_CHAR, ['r9', 0])
    program.add_instruction(Opcode.CMP, ['r9', 'r10'])
    program.add_instruction(Opcode.JE, [do_while_start + 7])
    program.add_instruction(Opcode.ADD_LIT, ['r11', 1])
    program.add_instruction(Opcode.ADD_LIT, ['r12', 1])
    program.add_instruction(Opcode.ST, ['r9', 'r12'])
    program.add_instruction(Opcode.JUMP, [do_while_start])
    program.add_instruction(Opcode.ST_ADDR, ['r11', static_mem_label])


# util func, сохранение значения по адресу(оба не в регистрах)
def st_lit_to_lit(program: Program, value: int | str, var_addr: int):
    reg = program.clear_register_for_variable()
    program.add_instruction(Opcode.LD_LIT, [reg, value])
    program.add_instruction(Opcode.ST_ADDR, [reg, var_addr])


def ast_to_machine_code_assign(node: AstNode, program: Program) -> None:
    name: str = node.children[0].value
    assert node.children[0].astType == AstType.NAME
    if node.astType == AstType.ASSIGN or node.astType == AstType.LET:
        addr = program.get_variable_offset(name)
        assert addr is not None
        if node.children[1].astType == AstType.STRING:
            addr_new = program.add_variable_in_static_mem(node.children[1].value, VariableType.STRING)
            st_lit_to_lit(program, addr_new, addr)
            program.clear_variable_in_registers(name)
        elif node.children[1].astType == AstType.READ:
            ast_to_machine_code_read(program)
            st_lit_to_lit(program, static_mem_label, addr)
            program.clear_variable_in_registers(name)
        else:
            ast_to_machine_code_math(node.children[1], program)
            program.add_instruction(Opcode.ST_ADDR, ['r9', addr])
            program.clear_variable_in_registers(name)


def ast_to_machine_code_let(node: AstNode, program: Program) -> None:
    name: str = node.children[0].value
    if node.astType == AstType.LET:
        assert program.get_variable_offset(name) is None

        if node.children[1].astType == AstType.STRING:
            var_addr_in_static_mem = program.add_variable_in_static_mem('0', VariableType.INT)
        else:
            var_addr_in_static_mem = program.add_variable_in_static_mem('0', VariableType.INT)
        program.variables[name] = var_addr_in_static_mem
        ast_to_machine_code_assign(node, program)


def ast_to_machine_code_print(node: AstNode, program: Program) -> None:
    if node.astType == AstType.PRINT_INT:
        ast_to_machine_code_math(node.children[0], program)
        program.add_instruction(Opcode.PRINT_CHAR, ['r9', 0])
    else:
        # todo print literal
        addr: int | None = program.get_variable_offset(node.children[0].value)
        assert addr is not None
        program.add_instruction(Opcode.LD_ADDR, ['r10', addr])  # адрес переменной, в которой указатель на значение
        program.add_instruction(Opcode.LD_ADDR, ['r11', addr])  # адрес переменной, в которой указатель на значение
        program.add_instruction(Opcode.INC, ['r11'])  # первый байт данных
        program.add_instruction(Opcode.LD, ['r9', 'r10'])  # теперь в r9 размер
        program.add_instruction(Opcode.LD_LIT, ['r10', 0])  # счётчик
        while_start: int = program.current_address
        program.add_instruction(Opcode.CMP, ['r9', 'r10'])
        program.add_instruction(Opcode.JE, [while_start + 7])
        program.add_instruction(Opcode.LD, ['r12', 'r11'])
        program.add_instruction(Opcode.PRINT_CHAR, ['r12', 0])
        program.add_instruction(Opcode.ADD_LIT, ['r10', 1])
        program.add_instruction(Opcode.ADD_LIT, ['r11', 1])
        program.add_instruction(Opcode.JUMP, [while_start])


def parse_expression(node: AstNode, program: Program) -> int | None:
    if node.astType == AstType.NAME:
        var_offs = program.get_variable_offset(node.value)
        return var_offs
    if node.astType == AstType.STRING:  # TODO check if string is in static memory
        addr = program.add_variable_in_static_mem(node.value, VariableType.STRING)
        return addr
    ast_to_machine_code_math(node, program)

source = 'test'
target = 'inp'

with open(source, encoding="utf-8") as f:
    source = f.read()

ast = parse(source)
write_code(target, ast_to_machine_code(ast))
# def main(source, target):
#     with open(source, encoding="utf-8") as f:
#         source = f.read()
#
#     ast = parse(source)
#     write_code(target, ast_to_machine_code(ast))

#
# if __name__ == "__main__":
#     assert len(sys.argv) == 2, "Wrong arguments: translator.py <input_file> <target_file>"
#     source, target = sys.argv
#     main(source, target)
