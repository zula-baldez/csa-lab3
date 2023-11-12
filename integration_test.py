import pytest


@pytest.mark.golden_test("golden/*.yml")
def test_hello(golden, caplog):
    """
    Вход:

    - `in_source` -- исходный код
    - `in_stdin` -- данные на ввод процессора для симуляции

    Выход:

    - `out_code` -- машинный код, сгенерированный транслятором
    - `out_stdout` -- стандартный вывод транслятора и симулятора
    - `out_log` -- журнал программы
    """
    print('hello')


