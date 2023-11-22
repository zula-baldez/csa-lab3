import json
from enum import Enum


class Opcode(Enum):
    LD = 'LD'
    LD_LIT = 'LD_LIT'
    MV = 'MV'
    INPUT = 'INPUT'
    PRINT = 'PRINT'
    JLE = 'JLE'  # less or equals
    JL = 'JL'  # less
    JGE = 'JGE'  # greater or equals
    JG = 'JG'  # greater
    JNE = 'JNE'  # not equals
    JE = 'JE'  # equals
    JUMP = 'JUMP'
    DIV = 'DIV'
    ADD = 'ADD'
    SUB = 'SUB'
    MUL = 'MUL'
    CMP = 'CMP'
    HALT = 'HTL'




class Word:
    index: int
    opcode: Opcode
    arg: list[int | str]

    def __init__(self, opcode: Opcode, arg: list[int | str]):
        self.opcode = opcode
        self.arg = arg


def write_code(filename, code):
    with open(filename, "w", encoding='utf-8') as file:
        file.write(json.dumps(code, indent=4))


def instruction_to_json(opcode: Opcode, index: int, arg: list[int | str]) -> dict[str, int | str]:
    return {
        'index': index,
        'opcode': opcode.value,
        'arg': arg
    }

# def write_code(filename, code):
#     with open(filename, "w", encoding='utf-8') as file:
#         file.write(json.dumps(code, indent=4))
#
# def read_code(filename):
#     with open(filename, encoding='utf-8') as file:
#         code = json.loads(file.read())
#
#     for instr in code:
#         instr['opcode'] = Opcode(instr['opcode'])
#     return code
