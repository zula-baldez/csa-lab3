import logging
import sys
from enum import Enum

from machine.isa import Opcode, Word, read_code, Register, sp, pc, dr


class Alu:
    neg: bool = False
    zero: bool = False
    carry: bool = False

    def __init__(self):
        self.acc = 0

    min_value = - 2 ** 32
    max_value = 2 ** 32 - 1

    def set_flags(self, value: int):
        self.carry = False
        if value > self.max_value:
            self.carry = True
            value = value & self.min_value
        if value < self.min_value:
            self.carry = True
            value = value & self.min_value
        self.neg = value < 0
        self.zero = value == 0

    def execute(self, opcode: Opcode, arg1: int, arg2: int = 0) -> int:
        res: int
        if opcode is Opcode.ADD or opcode is Opcode.ADD_LIT:
            res = arg1 + arg2
        elif opcode is Opcode.SUB:
            res = arg1 - arg2
        elif opcode is Opcode.MUL:
            res = arg1 * arg2
        elif opcode is Opcode.INC:
            res = arg1 + 1
        elif opcode is Opcode.DEC:
            res = arg1 - 1
        elif opcode is Opcode.SHR:
            res = arg1 >> arg2
        elif opcode is Opcode.SHL:
            res = 0 if arg1 == 0 else arg1 << arg2
        elif opcode is Opcode.XOR:
            res = arg1 ^ arg2
        elif opcode is Opcode.AND:
            res = arg1 & arg2
        elif opcode is Opcode.OR:
            res = arg1 | arg2
        elif opcode is Opcode.NEG:
            res = ~arg1
        else:
            raise ValueError("unknown opcode: {}".format(opcode))
        self.set_flags(res)

        return res


class DataPath:
    """Тракт данных (пассивный), включая: ввод/вывод, память и арифметику.


    - `signal_latch_reg_num` -- общий для всех регистров;
    - `signal_wr` -- запись в память данных;
    - `signal_output` -- вывод в порт;
    """
    registers: dict[Register, int] = {}

    mem_size: int = 0

    memory: list[Word] = []

    input_buffer: list[str] = None

    input_ports: dict[int, list[str]] = {}

    output_ports: dict[int, list[str]] = {}

    alu: Alu = None

    def __init__(self, data: list[Word], ports: dict[int, list[str]], mem_size: int = 4096):
        self.mem_size = mem_size
        self.memory = data
        self.alu = Alu()
        self.input_ports = ports
        self.output_ports[0] = []
        for reg_num in range(0, 15):
            self.registers[Register(reg_num)] = 0
        self.registers[sp] = self.mem_size - 1

    def latch_reg(self, reg: Register, value: int):
        self.registers[reg] = value

    def load_reg(self, reg: Register) -> int:
        return self.registers[reg]

    def _get_instruction(self, addr: int) -> Word:
        return self.memory[addr]

    def memory_perform(self, oe: bool, wr: bool, data: int = 0) -> Word | None:
        instr: Word = self._get_instruction(self.registers[dr])
        if oe:
            return instr
        if wr:
            instr.arg1 = data

    def perform_arithmetic(self, opcode: Opcode, arg1: int, arg2: int = 0) -> int:
        return self.alu.execute(opcode, arg1, arg2)

    def zero(self) -> bool:
        return self.alu.zero

    def neg(self) -> bool:
        return self.alu.neg

    def pick_char(self, port: int) -> int:
        if len(self.input_ports[port]) == 0:
            return 0
        return ord(self.input_ports[port].pop(0))

    def put_char(self, char: int, port: int):
        self.output_ports[port].append(chr(char))


class ControlUnit:
    class Stage(Enum):
        FETCH = 0
        DECODE = 1
        EXECUTE = 2

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
            addr = instr.arg1
            self.data_path.latch_reg(pc, addr)
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
                self.data_path.latch_reg(pc, instr.arg1)
            else:
                self.data_path.latch_reg(pc, self.data_path.registers[pc] + 1)
            self.tick()
            return True
        return False

    def fetch_instruction(self) -> Word:
        addr: int = self.data_path.registers[pc]
        self.data_path.latch_reg(dr, addr)
        self.tick()
        instr: Word = self.data_path.memory[self.data_path.registers[dr]]
        self.tick()
        return instr

    def ld_addr(self, instr: Word):
        addr: int = instr.arg2
        reg: Register = instr.arg1
        self.data_path.latch_reg(dr, addr)
        data: Word = self.data_path.memory_perform(True, False)
        self.tick()
        self.data_path.latch_reg(reg, data.arg1)
        self.tick()

    def ld_lit(self, instr: Word):
        val: int = instr.arg2
        reg: Register = instr.arg1
        self.data_path.latch_reg(reg, val)
        self.tick()

    def ld(self, instr: Word):
        word = self.data_path.memory[4095]
        reg_to: Register = instr.arg1
        reg_from: Register = instr.arg2
        reg_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg_from])
        self.tick()
        self.data_path.latch_reg(dr, reg_data)
        self.tick()
        data: Word = self.data_path.memory_perform(True, False)
        self.data_path.latch_reg(reg_to, data.arg1)
        self.tick()

    def ld_stack(self, instr: Word):
        reg_to: Register = instr.arg1
        addr: int = self.data_path.mem_size - instr.arg2 - 1
        self.tick()
        self.data_path.latch_reg(dr, addr)
        self.tick()
        data: Word = self.data_path.memory_perform(True, False)
        self.data_path.latch_reg(reg_to, data.arg1)
        self.tick()

    def st_addr(self, instr: Word):
        addr: int = instr.arg2
        self.data_path.latch_reg(dr, addr)
        self.tick()
        reg: Register = instr.arg1
        reg_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg])
        self.tick()
        self.data_path.memory_perform(False, True, reg_data)
        self.tick()

    def st(self, instr: Word):
        addr_reg: Register = instr.arg2
        addr: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[addr_reg])
        self.tick()
        self.data_path.latch_reg(dr, addr)
        self.tick()
        data_reg: Register = instr.arg1
        data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[data_reg])
        self.tick()
        self.data_path.memory_perform(False, True, data)
        self.tick()

    def st_stack(self, instr: Word):
        addr_to: int = self.data_path.mem_size - instr.arg2 - 1
        self.tick()
        self.data_path.latch_reg(dr, addr_to)
        self.tick()
        reg_from: Register = instr.arg1
        data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg_from])
        self.data_path.memory_perform(False, True, data)
        self.tick()

    def mv(self, instr: Word):
        reg_from: Register = instr.arg1
        reg_from_data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg_from])
        self.tick()
        reg_to: Register = instr.arg2
        self.data_path.latch_reg(reg_to, reg_from_data)
        self.tick()

    def read(self, instr: Word):
        reg: Register = instr.arg1
        port: int = instr.arg2
        data: int = self.data_path.pick_char(port)
        self.data_path.latch_reg(reg, data)
        self.tick()

    def print(self, instr: Word):
        reg: Register = instr.arg1
        data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[reg])
        port: int = instr.arg2
        self.tick()
        self.data_path.put_char(data, port)
        self.tick()

    def arythm(self, instr: Word):
        res: int = self.data_path.perform_arithmetic(instr.opcode, self.data_path.load_reg(instr.arg1),
                                                     self.data_path.load_reg(instr.arg2))
        self.tick()
        self.data_path.latch_reg(instr.arg1, res)
        self.tick()

    def add_lit(self, instr: Word):
        res: int = self.data_path.perform_arithmetic(instr.opcode, self.data_path.load_reg(instr.arg1), instr.arg2)
        self.tick()
        self.data_path.latch_reg(instr.arg1, res)
        self.tick()

    def push(self, instr: Word):
        addr_reg: Register = sp
        addr: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[addr_reg])
        self.tick()
        self.data_path.latch_reg(dr, addr)
        self.tick()
        data_reg: Register = instr.arg1
        data: int = self.data_path.perform_arithmetic(Opcode.ADD, 0, self.data_path.registers[data_reg])
        self.tick()
        self.data_path.memory_perform(False, True, data)
        self.tick()
        res: int = self.data_path.perform_arithmetic(Opcode.DEC, self.data_path.load_reg(sp))
        self.tick()
        self.data_path.latch_reg(sp, res)
        self.tick()

    def pop(self, instr: Word):
        res: int = self.data_path.perform_arithmetic(Opcode.INC, self.data_path.load_reg(sp))
        self.tick()
        self.data_path.latch_reg(sp, res)
        self.tick()
        addr: int = self.data_path.perform_arithmetic(Opcode.ADD, self.data_path.registers[sp], 0)
        self.tick()
        self.data_path.latch_reg(dr, addr)
        self.tick()
        data: Word = self.data_path.memory_perform(True, False)
        self.tick()
        self.data_path.latch_reg(instr.arg1, data.arg1)
        self.tick()


    def decode_and_execute_instruction(self):
        instr: Word = self.fetch_instruction()
        opcode: Opcode = instr.opcode

        if self.decode_and_execute_control_flow_instruction(instr, opcode):
            return
        if opcode is Opcode.LD_ADDR:
            self.ld_addr(instr)
        if opcode is Opcode.LD_LIT:
            self.ld_lit(instr)
        if opcode is Opcode.LD:
            self.ld(instr)
        if opcode is Opcode.LD_STACK:
            self.ld_stack(instr)
        if opcode is Opcode.ST_ADDR:
            self.st_addr(instr)
        if opcode is Opcode.ST:
            self.st(instr)
        if opcode is Opcode.ST_STACK:
            self.st_stack(instr)
        if opcode is Opcode.MV:
            self.mv(instr)
        if opcode is Opcode.READ:
            self.read(instr)
        if opcode is Opcode.PRINT:
            self.print(instr)
        if opcode in {Opcode.ADD, Opcode.MUL, Opcode.OR, Opcode.AND, Opcode.SHL, Opcode.SHR, Opcode.XOR, Opcode.SUB}:
            self.arythm(instr)
        if opcode in {Opcode.INC, Opcode.DEC}:
            res: int = self.data_path.perform_arithmetic(opcode, self.data_path.load_reg(instr.arg1))
            self.tick()
            self.data_path.latch_reg(instr.arg1, res)
            self.tick()

        if opcode is Opcode.ADD_LIT:
            self.add_lit(instr)
        if opcode is Opcode.CMP:
            res: int = self.data_path.perform_arithmetic(Opcode.SUB,
                                                         self.data_path.load_reg(instr.arg1),
                                                         self.data_path.load_reg(instr.arg2))
            self.tick()
        if opcode is Opcode.PUSH:
            self.push(instr)
        if opcode is Opcode.POP:
            self.pop(instr)
        self.data_path.latch_reg(pc, self.data_path.registers[pc] + 1)
        self.tick()

    def print_val_if_enum(self, value):
        if isinstance(value, Enum):
            return value.name
        return value

    def __repr__(self):
        formatted_registers = {f'r{register.value}': value for register, value in self.data_path.registers.items()}
        formatted_string = ', '.join([f"'{key}': {value}" for key, value in formatted_registers.items()])

        state_repr = "TICK: {:3} PC: {:3}  MEM_OUT: {} {} reg: {}".format(
            self._tick,
            self.data_path.registers[pc],
            self.print_val_if_enum(self.data_path.memory[self.data_path.registers[pc]].arg1),
            self.print_val_if_enum(self.data_path.memory[self.data_path.registers[pc]].arg2),
            formatted_string,
        )

        instr = self.data_path.memory[self.data_path.registers[pc]]
        opcode = str(instr.opcode)

        instr_repr = "  ('{}'@{}:{} {})".format(instr.index, opcode, instr.arg1, instr.arg2)

        return "{} \t{}".format(state_repr, instr_repr)


def simulation(mem: list[Word], input_tokens: list[str], limit: int):
    ports: dict[int, list[str]] = {}
    ports[0] = input_tokens
    data_path = DataPath(mem, ports)
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
    logging.info("output_buffer: %s", repr("".join(data_path.output_ports[0])))
    return "".join(data_path.output_ports[0]), instr_counter, control_unit.current_tick()


def main(code_file, input_file):
    code: list[Word] = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, instr_counter, ticks = simulation(
        code,
        input_tokens=input_token,
        limit=100000,
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 2, "Wrong arguments: emulator.py <code_file> <input_file>"
    code_file, input_file = sys.argv
    main(code_file, input_file)