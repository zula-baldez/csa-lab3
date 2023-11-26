import json
from enum import Enum


class Opcode(Enum):
    ST_ADDR = 'ST_ADDR'
    ST = 'ST'
    LD_ADDR = 'LD_ADDR'
    LD_LIT = 'LD_LIT'
    LD = 'LD'
    MV = 'MV'
    READ_CHAR = 'READ_CHAR'
    PRINT_CHAR = 'PRINT_CHAR'
    JLE = 'JLE'  # less or equals
    JL = 'JL'  # less
    JGE = 'JGE'  # greater or equals
    JG = 'JG'  # greater
    JNE = 'JNE'  # not equals
    JE = 'JE'  # equals
    JUMP = 'JUMP'
    DIV = 'DIV'
    ADD = 'ADD'
    ADD_LIT = 'ADD_LIT'
    SUB = 'SUB'
    MUL = 'MUL'
    CMP = 'CMP'
    PUSH = 'PUSH'
    POP = 'POP'
    INC = 'INC'
    DEC = 'DEC'
    HALT = 'HALT'


mem_size: int = 4096


class Word:
    index: int
    opcode: Opcode
    arg: list[int | str]

    def __init__(self, index: int, opcode: Opcode, arg=None):
        if arg is None:
            arg = []
        self.opcode = opcode
        self.arg = arg
        self.index = index


def write_code(filename: str, code: list[Word]) -> None:
    """Записать машинный код в файл."""
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps({
                "index": instr.index,
                "opcode": instr.opcode.value,  # Convert the Enum to its value
                "arg": instr.arg
            }
        ))
        file.write("[" + ",\n ".join(buf) + "]")


def read_code(filename) -> list[Word]:
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())
    prog: list[Word] = []
    for instr in code:
        word = Word(instr["index"], Opcode[instr["opcode"]], instr["arg"])
        prog.append(word)
    for index in range(len(prog), mem_size):
        prog.append(Word(index, Opcode.JUMP, [0]))
    return prog
