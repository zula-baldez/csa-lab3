alg | risc | neum | hw | tick | struct | stream | port | pstr | prob2 | pipeline

bnf
```
program ::= statement | program statement
statement ::= conditional | while | io | allocation | assign
assign ::= name "=" expr | name "++" | name "--" | compound_assign
compound_assign ::= name "+=" expr | name "-=" expr | name "*=" expr | name "/=" expr | name "%=" expr
io ::= read | print
conditional ::= if | else
if ::= "if" "(" comp_expr ")" "{" program "}"
else ::= "else" "{" program "}"
while ::= "while" "(" comp_expr ")" "{" program "}"
read ::= "read(" value ")" semicolon
print ::= "print(" value ")" semicolon
allocation ::= "let" name "=" value semicolon
value ::= string | number
string ::= "\"" "[a-zA-Z]+" "\""
comp_expr ::= expr comparison_sign expr
expr ::= "(" expr ")" | expr op expr | number | string | name
comparison_sign ::= "==" | ">=" | ">" | "<" | "<=" | "!="
name ::= "[a-zA-Z]+"
number ::= positive_number | neg_number
neg_number ::= "-" positive_number
positive_number ::= "[0-9]+"
semicolon ::= ";"
op ::= "*" | "/" | "%" | "+" | "-"
```
instruction set
    ST_LIT = 'ST_LIT'
    ST = 'ST'
    LD = 'LD'
    LD_LIT = 'LD_LIT'
    MV = 'MV'
    READ_CHAR = 'INPUT_CHAR'
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
    SUB = 'SUB'
    MUL = 'MUL'
    CMP = 'CMP'
    HALT = 'HTL'

https://miro.com/app/board/uXjVNPh5hBQ=/

### Набор инструкций

| Язык | Инструкция | Кол-во тактов | операнды                       |
|:-----|:-----------|---------------|:-------------------------------|
|      | ST_ADDR    | 3             | 2 (reg, addr(int)) - прямая    |
|      | ST         | 4             | 2 (reg, reg) - косвенная       |
|      | LD_ADDR    | 3             | 2 (reg, addr(int))             |
|      | LD_LIT     | 2             | 2 (reg, val from  instruction) |
|      | LD         | 4             | 2 (reg, reg)                   |
|      | MV         | 3             | 2 (reg, reg)                   |
|      | READ_CHAR  | 2             | 2 (reg, port)                  |
|      | PRINT_CHAR | 3             | 2 (reg, port)                  |
|      | JLE        | 2             | 1 (addr)                       |
|      | JL         | 0             | 1 (addr)                       |
|      | JGE        | 0             | 1 (addr)                       |
|      | JG         | 0             | 1 (addr)                       |
|      | JNE        | 0             | 1 (addr)                       |
|      | JE         | 0             | 1 (addr)                       |
|      | JUMP       | 0             | 1 (addr)                       |
|      | DIV        | ?             | ??                             |
|      | ADD        | 0             | 2 (reg, reg)                   |
|      | ADD_LIT    | 0             | 2 (reg, val)                   |
|      | SUB        | 0             | ??                             |
|      | MUL        | 0             | 2(reg1, reg2)                  |
|      | CMP        | 0             | 2(reg1, reg2)                  |
|      | PUSH       | 0             | 1(reg)                         |
|      | POP        | 0             | 1(reg)                         |
|      | HALT       | 0             | 0                              |
21 команда - 5(6) бит на опкод и по 13 на 1 и 2 аргумент
bnf

expr   ::= factor
        |  expr "+" factor
factor ::= number
        |  factor "*" number
number ::= digit
        |  number digit
operation ::= "+" | "*" | "/" | "%"
digit  ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
