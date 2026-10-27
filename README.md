# Languages and Compilers — Project Stage 2

## Overview

This project extends the custom programming language from Stage 1 with functions, structures, member functions, input/output operations, semantic analysis, and LLVM IR code generation.

The original Stage 1 syntax (`num32`, `num64`, `bool`, `mut`, `:=`, `if/else`) remains supported.

## Setup and Usage

Requirements: Python 3, `llvmlite`, and Clang.

```bash
python3 -m pip install llvmlite

# Print AST
python3 compiler.py --ast tests/ok/if_else.txt

# Generate LLVM IR
python3 compiler.py tests/stage2_ok/project_spelling.txt output.ll

# Compile and run
clang output.ll -o program
./program
```

Compilation errors are reported to stderr as:

```text
compilation error: line L:C: message
```

Compilation failures return a non-zero exit code and do not create an output file.

## Language Features

### 1. Variables and Conditions (Stage 1)

Types are `num32` (32-bit integer), `num64` (64-bit integer), and `bool`. Variables are immutable unless declared with `mut`.

```text
num32 mut x{5};
x := x + 3;

if x == 8 {
    print(x);
} else {
    print(0);
}
```

Arithmetic supports `+`, `-`, `*`, `/`, parentheses, and comparisons `==`, `!=`.

### 2. Functions

Functions have typed parameters, a result type, and an `exit` statement. Calls are expressions and may be nested, recursive, or reference functions declared later.

```text
fn twice := (num32 x) -> num32 {
    exit x + x
}

num32 result{twice(twice(3))};
print(result);
exit 0
```

**Rules:** Arguments must match parameter count and types. Return values must match the declared result type. Function signatures are collected before function bodies are checked, allowing recursion and forward calls.

### 3. Structures and Fields

Structures contain typed, mutable or immutable fields. Objects must initialize every field in declaration order. Field access may be nested.

```text
struct Point {
    num32 mut x
    num32 y
}

Point mut p{3, 4};
p.x := 7;
print(p);
exit 0
```

**Rules:** Fields must exist. Assignments require every relevant link in the access chain to be mutable. Immutable fields cannot be reassigned.

### 4. Member Functions

Member functions are declared inside structures and can access their fields directly.

```text
struct Counter {
    num32 mut value

    fn add := (num32 amount) -> num32 {
        value := value + amount
        exit value
    }
}

Counter mut c{4};
print(c.add(3));
exit 0
```

**Rules:** A member function that modifies fields requires a mutable receiver. Inside a member function, names are resolved in this order: parameters and locals, then structure fields and methods, then globals.

### 5. Input and Output

`read()` reads one integer from stdin and returns `num32`. It accepts no arguments.

`print()` accepts one integer, boolean, string literal, or structure object and adds a newline.

```text
num32 x{read()};
print("Input:");
print(x);
exit 0
```

Booleans print as `true` or `false`. Objects print as `Point{x: 3, y: 4}`, in field declaration order, including nested objects. `num32` uses `%d`; `num64` uses `%lld`.

## Semantic Analysis

A separate semantic pass checks the AST before LLVM IR generation.

| Rule | Validation |
|---|---|
| Names and scopes | Declaration before use; no duplicate declarations in one scope |
| Types | Compatible assignment, expression, parameter, and return types |
| Mutability | No writes to constant variables, fields, or immutable chains |
| Functions | Correct argument count and types; valid results |
| Structures | Existing fields, correct initializers and field types |
| Methods | Mutating methods require mutable objects |
| Conversions | `num32` may widen to `num64`; implicit narrowing is rejected |
| Overflow | Integer literal bounds are checked; runtime arithmetic has no overflow traps |

`bool` cannot be used in numeric arithmetic. Each function must return a compatible value using `exit`. Stage 1 programs may omit a top-level `exit`.

## LLVM IR Generation

LLVM IR is generated through `llvmlite.ir.IRBuilder`, not manually assembled strings.

- Variables use `alloca`, `store`, and `load`.
- Conditions use basic blocks and conditional branches.
- Functions are declared before their bodies; internal names avoid runtime symbol conflicts.
- Structures use identified LLVM types and field indexes accessed through GEP.
- Member functions receive the object pointer as an implicit first parameter.
- `read()` and `print()` use external `scanf` and `printf` declarations with global format strings.

## Testing

```bash
python3 run_tests.py
python3 run_stage2_tests.py
```

| Tests | Valid | Invalid |
|---|---:|---:|
| Stage 1 | 18 | 17 |
| Stage 2 | 16 | 10 |
| **Total** | **34** | **27** |

Latest verified results: **35/35 Stage 1** and **26/26 Stage 2** tests passed.

Stage 2 valid tests compile to LLVM IR, build with Clang, execute, and compare exact stdout with `.expected` files. Tests with `.in` files provide stdin. Invalid tests compare compiler diagnostics with expected errors.

Tests cover functions, recursion, structures, fields, methods, input/output, invalid arguments, incorrect result types, unknown fields, and immutable assignments.

## Project Structure

- `compiler.py` — CLI and Stage 1 compatibility.
- `src/stage1_frontend.py` — original lexer, parser, and AST.
- `src/engine.py` — extended lexer/parser, semantic checks, and LLVM generator.
- `grammar.ebnf` — language grammar.
- `tests/` — valid and invalid examples.
- `run_tests.py`, `run_stage2_tests.py` — test scripts.

## Optional Bonus: VS Code Extension

`vscode-stage2-syntax/` contains a syntax-highlighting extension for the custom language. Open the extension folder in VS Code, press `F5`, and open a `.stage2` file to test highlighting.

## Known Limitations

Some Stage 2 diagnostics may reference positions in normalized source rather than the original input because the compiler uses a syntax compatibility layer. This requires further correction to fully satisfy source-position requirements.

## Submission

Stage 2 is developed in the `stage2` branch created from `main`. Submit a pull request into `main`, request `vovaskochko` as reviewer, and do not merge before review.

Submit the PR link and completed `ai_usage_2.txt` in Moodle. The original Stage 1 disclosure remains in `ai_usage.txt`.
