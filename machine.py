import logging
import sys
from enum import Enum

from isa import Opcode, Word, read_code


class Alu:
    neg: bool = False
    zero: bool = False

    def __init__(self):
        self.acc = 0

    def set_flags(self, value: int):
        """Установить флаги `neg` и `zero`."""
        self.neg = value < 0
        self.zero = value == 0

    def execute(self, opcode: Opcode, arg1: int, arg2: int = 0) -> int:
        """Выполнить команду `opcode` с аргументом `arg`."""
        if opcode is Opcode.ADD or opcode is Opcode.ADD_LIT:
            res = arg1 + arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.SUB:  # todo IMPLEMENT
            res = arg1 - arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.MUL:
            res = arg1 * arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.INC:
            res = arg1 + 1
            self.set_flags(res)
            return res
        elif opcode is Opcode.DEC:
            res = arg1 - 1
            self.set_flags(res)
            return res
        else:
            raise ValueError("unknown opcode: {}".format(opcode))


class DataPath:
    """Тракт данных (пассивный), включая: ввод/вывод, память и арифметику.


    - `signal_latch_reg_num` -- общий для всех регистров;
    - `signal_wr` -- запись в память данных;
    - `signal_output` -- вывод в порт;
    """
    registers: dict[int, int] = {}

    mem_size: int = 4096

    memory: list[Word] = []

    input_buffer: list[str] = None

    output_buffer: list[str] = None

    alu: Alu = None

    def __init__(self, data: list[Word], input_buffer: list[str]):
        self.memory = data
        self.input_buffer = input_buffer
        self.output_buffer = []
        self.alu = Alu()
        for reg_num in range(0, 15):
            self.registers[reg_num] = 0
        self.registers[15] = self.mem_size - 1

    def latch_reg(self, reg_num: int, value: int):
        self.registers[reg_num] = value

    def load_reg(self, reg_num: int) -> int:
        return self.registers[reg_num]

    def _get_instruction(self, addr: int) -> Word:
        return self.memory[addr]

    def memory_perform(self, oe: bool, wr: bool, data: int = 0) -> Word | None:
        instr: Word = self._get_instruction(self.registers[14])
        if oe:
            return instr
        if wr:
            instr.arg = [data]

    def perform_arithmetic(self, opcode: Opcode, arg1: int, arg2: int = 0) -> int:
        return self.alu.execute(opcode, arg1, arg2)

    def zero(self) -> bool:
        return self.alu.zero

    def neg(self) -> bool:
        return self.alu.neg

    def pick_char(self) -> int:
        if len(self.input_buffer) == 0:
            return 0
        return ord(self.input_buffer.pop())

    def put_char(self, char: int):
        self.output_buffer.append(chr(char))


class ControlUnit:
    class Stage(Enum):
        """Этап выполнения команды. В теории для конвейеризации."""
        FETCH = 0
        DECODE = 1
        EXECUTE = 2

    # program counter r13

    data_path: DataPath = None

    _tick: int = 0

    def __init__(self, data_path):
        self._tick = 0
        self.data_path = data_path

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def decode_and_execute_control_flow_instruction(self, instr, opcode) -> bool:
        if opcode is Opcode.HALT:
            raise StopIteration()

        if opcode is Opcode.JUMP:
            addr = instr.arg[0]
            self.data_path.latch_reg(13, addr)
            self.tick()
            return True

        jmp_flag: bool = False

        if (opcode is Opcode.JE or opcode is Opcode.JNE or opcode is Opcode.JL or opcode is Opcode.JLE or
                opcode is Opcode.JG or opcode is Opcode.JGE):
            match opcode:
                case Opcode.JE:
                    jmp_flag = self.data_path.zero() == 1
                case Opcode.JNE:
                    jmp_flag = self.data_path.zero() == 0
                case Opcode.JG:
                    jmp_flag = self.data_path.neg() == 0
                case Opcode.JGE:
                    jmp_flag = self.data_path.neg() == 0 or self.data_path.zero() == 1
                case Opcode.JL:
                    jmp_flag = self.data_path.neg() == 1
                case Opcode.JLE:
                    jmp_flag = self.data_path.neg() == 1 or self.data_path.zero() == 1
            if jmp_flag:
                self.data_path.latch_reg(13, instr['arg'])
            else:
                self.data_path.latch_reg(13, self.data_path.registers[13] + 1)
            self.tick()
            return True
        return False

    def parse_reg(self, reg: str) -> int:
        return int(reg[1:])

    def fetch_instruction(self) -> Word:
        addr: int = self.data_path.registers[13]
        self.data_path.latch_reg(14, addr)
        self.tick()
        instr: Word = self.data_path.memory[self.data_path.registers[14]]
        self.tick()
        return instr

    def decode_and_execute_instruction(self):
        instr: Word = self.fetch_instruction()
        opcode: Opcode = instr.opcode

        if self.decode_and_execute_control_flow_instruction(instr, opcode):
            return
        if opcode is Opcode.LD_ADDR:
            addr: int = instr.arg[1]
            reg: int = self.parse_reg(instr.arg[0])
            self.data_path.latch_reg(14, addr)
            data: Word = self.data_path.memory_perform(True, False)
            self.tick()
            self.data_path.latch_reg(reg, data.arg[0])
            self.tick()
        if opcode is Opcode.LD_LIT:
            val: int = instr.arg[1]
            reg: int = self.parse_reg(instr.arg[0])
            self.data_path.latch_reg(reg, val)
            self.tick()
        if opcode is Opcode.LD:
            reg_from: int = self.parse_reg(instr.arg[0])
            reg_to: int = self.parse_reg(instr.arg[1])
            reg_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg_from])
            self.tick()
            self.data_path.latch_reg(14, reg_data)
            self.tick()
            data: Word = self.data_path.memory_perform(True, False)
            self.data_path.latch_reg(reg_to, data.arg[0])
            self.tick()
        if opcode is Opcode.ST_ADDR:
            addr: int = instr.arg[1]
            self.data_path.latch_reg(14, addr)  # data from command itself
            self.tick()
            reg: int = self.parse_reg(instr.arg[0])
            reg_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg])
            self.tick()
            self.data_path.memory_perform(False, True, reg_data)
            self.tick()
        if opcode is Opcode.ST:
            addr_reg: int = instr.arg[1]
            addr: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[addr_reg])
            self.tick()
            self.data_path.latch_reg(14, addr)
            self.tick()
            data_reg: int = self.parse_reg(instr.arg[0])
            data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[data_reg])
            self.tick()
            self.data_path.memory_perform(False, True, data)
            self.tick()
        if opcode is Opcode.MV:
            reg_from: int = instr.arg[0]
            reg_from_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg_from])
            self.tick()
            reg_to = self.parse_reg(instr.arg[1])
            self.data_path.latch_reg(reg_to, reg_from_data)
            self.tick()
        if opcode is Opcode.READ_CHAR:
            reg: int = self.parse_reg(instr.arg[0])
            data: int = self.data_path.pick_char()
            self.data_path.latch_reg(reg, data)
            self.tick()
        if opcode is Opcode.PRINT_CHAR:
            reg: int = self.parse_reg(instr.arg[0])
            data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg])
            self.tick()
            self.data_path.put_char(data)
            self.tick()
        if opcode in {Opcode.ADD, Opcode.MUL}:
            res: int = self.data_path.perform_arithmetic(opcode, self.data_path.load_reg(self.parse_reg(instr.arg[0])),
                                                         self.data_path.load_reg(self.parse_reg(instr.arg[1])))
            self.tick()
            self.data_path.latch_reg(self.parse_reg(instr.arg[0]), res)
            self.tick()
        if opcode is Opcode.ADD_LIT:
            res: int = self.data_path.perform_arithmetic(opcode, self.data_path.load_reg(self.parse_reg(instr.arg[0])),
                                                         instr.arg[1])
            self.tick()
            self.data_path.latch_reg(self.parse_reg(instr.arg[0]), res)
            self.tick()
        if opcode is Opcode.CMP:
            res: int = self.data_path.perform_arithmetic(Opcode.SUB,
                                                         self.data_path.load_reg(self.parse_reg(instr.arg[0])),
                                                         self.data_path.load_reg(self.parse_reg(instr.arg[1])))
            self.tick()
        if opcode is Opcode.PUSH:
            addr_reg: int = 15  # SP
            addr: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[addr_reg])
            self.tick()
            self.data_path.latch_reg(14, addr)
            self.tick()
            data_reg: int = self.parse_reg(instr.arg[0])
            data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[data_reg])
            self.tick()
            self.data_path.memory_perform(False, True, data)
            self.tick()
            res: int = self.data_path.perform_arithmetic(Opcode.DEC, self.data_path.load_reg(15))
            self.tick()
            self.data_path.latch_reg(15, res)
            self.tick()
        if opcode is Opcode.POP:
            res: int = self.data_path.perform_arithmetic(Opcode.INC, self.data_path.load_reg(15))
            self.tick()
            self.data_path.latch_reg(15, res)
            self.tick()
            addr: int = self.data_path.perform_arithmetic(Opcode.ADD, self.data_path.registers[15], 0)
            self.tick()
            self.data_path.latch_reg(14, addr)
            self.tick()
            data: Word = self.data_path.memory_perform(True, False)
            self.tick()
            self.data_path.latch_reg(self.parse_reg(instr.arg[0]), data.arg[0])
            self.tick()
        self.data_path.latch_reg(13, self.data_path.registers[13] + 1)
        self.tick()

    def __repr__(self):
        """Вернуть строковое представление состояния процессора."""
        state_repr = "TICK: {:3} PC: {:3}  MEM_OUT: {} reg: {}".format(
            self._tick,
            self.data_path.registers[13],
            self.data_path.memory[self.data_path.registers[13]].arg,
            self.data_path.registers,
        )

        instr = self.data_path.memory[self.data_path.registers[13]]
        opcode = str(instr.opcode)

        instr_repr = "  ('{}'@{}:{})".format(instr.index, opcode, instr.arg)

        return "{} \t{}".format(state_repr, instr_repr)


def simulation(mem: list[Word], input_tokens: list[str], limit: int):
    """Подготовка модели и запуск симуляции процессора.

    Длительность моделирования ограничена:

    - количеством выполненных инструкций (`limit`);

    - количеством данных ввода (`input_tokens`, если ввод используется), через
      исключение `EOFError`;

    - инструкцией `Halt`, через исключение `StopIteration`.
    """
    data_path = DataPath(mem, input_tokens)
    control_unit = ControlUnit(data_path)
    instr_counter = 0

    logging.debug("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))
    return "".join(data_path.output_buffer), instr_counter, control_unit.current_tick()


#
# input_token = 'penis'
# c = []
# code = code.split('\n')
# for i in code:
#     c.append(ast.literal_eval(i))
#
# for i in c:
#     i['opcode'] = Opcode[i['opcode']]
# output, instr_counter, ticks = simulation(
#     c,
#     input_tokens=input_token,
#     data_memory_size=100,
#     limit=1000,
# )
# code_file = 'test'
# input_file = 'inp'
#
# code: list[Word] = read_code(code_file)
# with open(input_file, encoding="utf-8") as file:
#     input_text = file.read()
#     input_token = []
#     for char in input_text:
#         input_token.append(char)
#
# output, instr_counter, ticks = simulation(
#     code,
#     input_tokens=input_token,
#     limit=1000,
# )
#
# print("".join(output))
# print("instr_counter: ", instr_counter, "ticks:", ticks)
# logging.getLogger().setLevel(logging.DEBUG)


def main(code_file, input_file):
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции.
    """
    code: list[Word] = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, instr_counter, ticks = simulation(
        code,
        input_tokens=input_token,
        limit=1000,
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 2, "Wrong arguments: machine.py <code_file> <input_file>"
    code_file, input_file = sys.argv
    main(code_file, input_file)
