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



    WR = 'wr'
    LD = 'ld'
    INPUT = 'input'
    PRINT = 'print'
    JLE = 'jle'  #less or equals
    JL = 'jl'  #less
    JGE = 'jge'  #greater or equals
    JG = 'jg'  #greater
    JNE = 'jne'  #not equals
    JE = 'je'  #equals
    DIV = 'div'
    ADD = 'add'
    SUB = 'sub'
    MUL = 'mul'
    INC = 'inc'
    DEC = 'dec'
    JUMP = 'jmp'
    PUSH = 'push'
    POP = 'pop'
    HALT = 'hlt'

https://miro.com/app/board/uXjVNPh5hBQ=/

bnf

expr   ::= factor
        |  expr "+" factor
factor ::= number
        |  factor "*" number
number ::= digit
        |  number digit
operation ::= "+" | "*" | "/" | "%"
digit  ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
