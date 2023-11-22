import ast
import logging
import sys
from enum import Enum

from isa import Opcode, Word


class Alu:
    neg: bool = False

    zero: bool = False

    def __init__(self):
        self.acc = 0

    def set_flags(self, value: int):
        """Установить флаги `neg` и `zero`."""
        self.neg = value < 0
        self.zero = value == 0

    def execute(self, opcode: Opcode, arg1: int, arg2: int) -> int:
        """Выполнить команду `opcode` с аргументом `arg`."""
        if opcode is Opcode.ADD:
            res = arg1 + arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.SUB:
            res = arg1 - arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.MUL:
            res = arg1 * arg2
            self.set_flags(res)
            return res
        elif opcode is Opcode.DIV:
            res = arg1 // arg2
            self.set_flags(res)
            return res
        else:
            raise ValueError("unknown opcode: {}".format(opcode))


class DataPath:
    """Тракт данных (пассивный), включая: ввод/вывод, память и арифметику.


    - `signal_latch_reg_num` -- общий для всех регистров;
    - `signal_wr` -- запись в память данных;
    - `signal_output` -- вывод в порт;

    Сигнал "исполняется" за один такт. Корректность использования сигналов --
    задача `ControlUnit`.
    """
    reg: dict[int, int] = {}

    mem_size: int = 0

    memory: list[dict] = []

    input_buffer = None

    output_buffer = None

    alu: Alu = None

    def __init__(self, data: list[dict], input_buffer):
        self.data = data
        self.input_buffer = input_buffer
        self.output_buffer = []
        self.alu = Alu()

    def latch_reg(self, reg_num: int, value: int):
        self.reg[reg_num] = value

    def load_reg(self, reg_num: int) -> int:
        return self.reg[reg_num]

    def _get_instruction(self, addr: int) -> dict:
        return self.data[addr]

    def memory_perform(self, oe: bool, wr: bool, addr: int, data: int = 0) -> dict | None:
        instr: dict = self._get_instruction(addr)
        if oe:
            return instr
        if wr:
            instr["arg"] = data

    def perform_arithmetic(self, opcode: Opcode, arg1: int, arg2: int) -> int:
        return self.alu.execute(opcode, arg1, arg2)

    def zero(self) -> bool:
        return self.alu.zero

    def neg(self) -> bool:
        return self.alu.neg


class ControlUnit:
    class Stage(Enum):
        """Этап выполнения команды. В теории для конвейеризации."""
        FETCH = 0
        DECODE = 1
        EXECUTE = 2

    program_counter: int = 0

    data_path: DataPath = None

    _tick: int = 0

    def __init__(self, data_path):
        self._tick = 0
        self.data_path = data_path
        self.program_counter = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        """Текущее модельное время процессора (в тактах)."""
        return self._tick

    def signal_latch_program_counter(self, sel_next: bool):
        """Защёлкнуть новое счётчика команд.

        Если `sel_next` равен `True`, то счётчик будет увеличен на единицу,
        иначе -- будет установлен в значение аргумента текущей инструкции.
        """
        if sel_next:
            self.program_counter += 1
        else:
            instr = self.program[self.program_counter]
            assert "arg" in instr, "internal error"
            self.program_counter = instr["arg"]

    def decode_and_execute_control_flow_instruction(self, instr, opcode):
        """Декодировать и выполнить инструкцию управления потоком исполнения. В
        случае успеха -- вернуть `True`, чтобы перейти к следующей инструкции.
        """
        if opcode is Opcode.HALT:
            raise StopIteration()

        if opcode is Opcode.JUMP:
            addr = instr["arg"]
            self.program_counter = addr
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
                self.data_path.latch_reg(14, instr['arg'])

            # self.data_path.signal_latch_acc()
            self.tick()
            if self.data_path.zero():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()
            return True
        return False

    def parse_reg(self, reg: str) -> int:
        """Преобразовать строку в номер регистра."""
        return int(reg[1:])

    def decode_and_execute_instruction(self):
        """Основной цикл процессора. Декодирует и выполняет инструкцию.

        Обработка инструкции:

        1. Проверить `Opcode`.

        2. Вызвать методы, имитирующие необходимые управляющие сигналы.

        3. Продвинуть модельное время вперёд на один такт (`tick`).

        4. (если необходимо) повторить шаги 2-3.

        5. Перейти к следующей инструкции.

        Обработка функций управления потоком исполнения вынесена в
        `decode_and_execute_control_flow_instruction`.
        """
        instr = self.data_path.data[self.program_counter]
        opcode = instr["opcode"]

        if self.decode_and_execute_control_flow_instruction(instr, opcode):
            return

        if opcode in {Opcode.LD, Opcode.LD_LIT}:
            self.data_path.memory_perform(False, True, self.parse_reg(instr["arg"][0]))
            self.tick()
            self.signal_latch_program_counter(sel_next=True)
            self.tick()

        elif opcode in {Opcode.MV}:
            self.data_path.latch_reg(self.parse_reg(instr["arg"][0]), self.parse_reg(instr["arg"][1]))
            self.tick()
            self.signal_latch_program_counter(sel_next=True)
            self.tick()
        elif opcode in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV}:
            self.data_path.perform_arithmetic(opcode, self.data_path.load_reg(self.parse_reg(instr["arg"][0])),
                                              self.data_path.load_reg(self.parse_reg(instr["arg"][1])))
            self.tick()
            self.signal_latch_program_counter(sel_next=True)
            self.tick()


    def __repr__(self):
        """Вернуть строковое представление состояния процессора."""
        # ADDR: {:3} ???
        state_repr = "TICK: {:3} PC: {:3}  MEM_OUT: {} reg: {}".format(
            self._tick,
            self.program_counter,
            self.data_path.memory[self.program_counter],
            self.data_path.reg,
        )

        instr = self.program[self.program_counter]
        opcode = instr["opcode"]
        instr_repr = str(opcode)

        if "arg" in instr:
            instr_repr += " {}".format(instr["arg"])

        if "term" in instr:
            term = instr["term"]
            instr_repr += "  ('{}'@{}:{})".format(term.symbol, term.line, term.pos)

        return "{} \t{}".format(state_repr, instr_repr)


def simulation(code, input_tokens, data_memory_size, limit):
    """Подготовка модели и запуск симуляции процессора.

    Длительность моделирования ограничена:

    - количеством выполненных инструкций (`limit`);

    - количеством данных ввода (`input_tokens`, если ввод используется), через
      исключение `EOFError`;

    - инструкцией `Halt`, через исключение `StopIteration`.
    """
    data_path = DataPath(code, input_tokens)
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

code = '''{'index': 0, 'opcode': 'LD', 'arg': ['r13', 4]}
{'index': 1, 'opcode': 'LD_LIT', 'arg': ['r1', 10]}
{'index': 2, 'opcode': 'MV', 'arg': ['r1', 'r11']}
{'index': 3, 'opcode': 'LD_LIT', 'arg': ['r2', 10]}
{'index': 4, 'opcode': 'MV', 'arg': ['r2', 'r12']}
{'index': 5, 'opcode': 'MUL', 'arg': ['r10', 'r11', 'r10']}
{'index': 6, 'opcode': 'LD_LIT', 'arg': ['r3', 20]}
{'index': 7, 'opcode': 'MV', 'arg': ['r3', 'r11']}
{'index': 8, 'opcode': 'LD_LIT', 'arg': ['r4', 20]}
{'index': 9, 'opcode': 'MV', 'arg': ['r4', 'r12']}
{'index': 10, 'opcode': 'MUL', 'arg': ['r11', 'r12', 'r11']}
{'index': 11, 'opcode': 'ADD', 'arg': ['r10', 'r11', 'r10']}
{'index': 12, 'opcode': 'CMP', 'arg': ['r13', 'r10']}
{'index': 13, 'opcode': 'JG', 'arg': ['r5', 16]}
{'index': 14, 'opcode': 'PRINT', 'arg': ['r11']}
{'index': 15, 'opcode': 'JUMP', 'arg': 0}
{'index': 16, 'opcode': 'JUMP', 'arg': 0}'''

input_token = 'penis'
c = []
code = code.split('\n')
for i in code:
    c.append(ast.literal_eval(i))

for i in c:
    i['opcode'] = Opcode[i['opcode']]
output, instr_counter, ticks = simulation(
    c,
    input_tokens=input_token,
    data_memory_size=100,
    limit=1000,
)

# def main(code_file, input_file):
#     """Функция запуска модели процессора. Параметры -- имена файлов с машинным
#     кодом и с входными данными для симуляции.
#     """
#     code = read_code(code_file)
#     with open(input_file, encoding="utf-8") as file:
#         input_text = file.read()
#         input_token = []
#         for char in input_text:
#             input_token.append(char)
#
#     output, instr_counter, ticks = simulation(
#         code,
#         input_tokens=input_token,
#         data_memory_size=100,
#         limit=1000,
#     )
#
#     print("".join(output))
#     print("instr_counter: ", instr_counter, "ticks:", ticks)
#
#
# if __name__ == "__main__":
#     logging.getLogger().setLevel(logging.DEBUG)
#     assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
#     _, code_file, input_file = sys.argv
#     main(code_file, input_file)
