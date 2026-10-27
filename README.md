# Languages and Compilers Course Project

This repository contains Stage 1 of the Languages and Compilers course project.

The project implements a small programming language with a hand-written byte-based lexer, a recursive-descent parser, and an Abstract Syntax Tree (AST).

## Language Syntax and Features

### Integer Types

The language supports two integer types: `num32` and `num64`.

```text
num32 x { 10 };
num64 y { 100 };
```

### Integer Overflow

Integer literal values are checked against the range of their declared type.

`num32` supports values from `0` to `2147483647`.

`num64` supports values from `0` to `9223372036854775807`.

The following declarations are valid:

```text
num32 x { 2147483647 };
num64 y { 9223372036854775807 };
```

A literal value larger than the maximum value of its declared integer type causes a compilation error.

```text
num32 x { 2147483648 };
```

Negative integer literals are not part of the current language grammar.

### Boolean Type

The language supports the `bool` type and the boolean values `true` and `false`.

```text
bool active { true };
bool ready { false };
```

### Immutable Variables

A variable is immutable by default.

```text
num32 x { 10 };
```

### Mutable Variables

The `mut` keyword declares a mutable variable.

```text
num32 mut x { 10 };
```

### Assignment

Assignment uses the `:=` operator.

```text
num32 mut x { 10 };
x := 20;
```

### Arithmetic Expressions

The language supports `+`, `-`, `*`, and `/`.

```text
num32 a { 1 + 2 };
num32 b { 5 - 2 };
num32 c { 2 * 3 };
num32 d { 8 / 2 };
```

Normal arithmetic precedence is supported.

```text
num32 x { 1 + 2 * 3 };
```

Parentheses can be used to change the evaluation order.

```text
num32 x { (1 + 2) * 3 };
```

### Comparison Operators

The language supports equality and inequality comparisons using `==` and `!=`.

```text
bool same { 10 == 10 };
bool different { 10 != 20 };
```

### If Statement

An `if` statement contains a condition and at least one statement in its block.

```text
bool active { true };
num32 mut x { 10 };

if active {
    x := 20;
}
```

### If / Else Statement

The `else` block is optional. If present, it must also contain at least one statement.

```text
bool active { true };
num32 mut x { 10 };

if active {
    x := 20;
} else {
    x := 30;
}
```

### Nested If Statements

`if` statements can be nested.

```text
bool active { true };
bool ready { false };
num32 mut x { 10 };

if active {
    if ready {
        x := 20;
    } else {
        x := 30;
    }
}
```

## Grammar

The complete EBNF grammar is stored in:

```text
grammar.ebnf
```

The parser accepts the syntax described by this grammar.

The language uses a custom declaration syntax in which the initializer expression is placed inside braces.

```text
num32 x { 10 };
```

Mutable variables use the `mut` keyword:

```text
num32 mut x { 10 };
```

Assignment uses `:=`:

```text
x := 20;
```

## Lexer

The lexer is hand-written and processes source code as bytes.

Each token stores:

- token kind;
- token text;
- line number;
- column number.

The lexer does not use regular expressions, `split()`, a lexer generator, or another generated lexer implementation.

## Parser and AST

The parser is implemented using recursive descent.

It reads the token stream produced by the lexer and builds an Abstract Syntax Tree.

The AST contains a class hierarchy for programs, statements, expressions, declarations, assignments, if statements, binary expressions, literals, and identifiers.

Each AST node stores its source line and column.

## Build Requirements

The compiler is implemented in Python 3.

There are no external dependencies and no separate build step is required.

Check that Python 3 is installed:

```bash
python3 --version
```

The compiler source can also be checked for Python syntax errors with:

```bash
python3 -m py_compile compiler.py
```

## Running the Compiler

Place a program in a source file such as `input.txt`.

Run:

```bash
python3 compiler.py --ast input.txt
```

Example `input.txt`:

```text
num32 mut x { 10 };
num64 y { 100 };
bool active { true };

x := 20;

if active {
    x := 30;
} else {
    x := 40;
}
```

The compiler prints an indented description of the generated AST.

## Error Reporting

Lexical and syntax errors are printed to standard error in the following format:

```text
compilation error: line L:C: message
```

The compiler exits with a non-zero exit code when compilation fails and does not print an AST.

Integer literal overflow errors use the same error format.

## Running the Tests

Valid programs and their expected AST output are stored in:

```text
tests/ok/
```

Invalid programs and their expected error output are stored in:

```text
tests/err/
```

Each `.txt` test file has a corresponding `.expected` file.

Run the complete test suite with:

```bash
python3 run_tests.py
```

The test runner executes all valid and invalid cases, compares actual output with the expected output, and reports passed and failed tests.

The current test suite contains:

```text
18 valid tests
17 error tests
35 tests total
```

## Project Structure

```text
.
├── README.md
├── ai_usage.txt
├── compiler.py
├── grammar.ebnf
├── input.txt
├── run_tests.py
└── tests
    ├── ok
    └── err
```

## Stage 1 Scope

Stage 1 implements:

- the language syntax and EBNF grammar;
- a hand-written byte-based lexer;
- a recursive-descent parser;
- an AST class hierarchy;
- AST output;
- lexical and syntax error reporting;
- integer literal overflow checks for `num32` and `num64`;
- automated valid and invalid test cases.

Full semantic analysis and code generation are not implemented in Stage 1.
