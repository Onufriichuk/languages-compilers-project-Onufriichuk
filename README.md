# Languages and Compilers — Project Stage 3

## Overview

This project implements a custom programming language compiler using Python and `llvmlite`. The compiler generates LLVM IR and supports native compilation through `llc` and `clang`.

The language supports variables, `num32`, `num64`, `bool`, arithmetic, conditions, `while` loops, functions, structures, member functions, `read()` and `print()`.

Stage 3 adds:
- **Task 1:** Integer-range `for` loops and bonus `break`.
- **Task 2:** AST optimization with unused variable elimination, unused function elimination, and function inlining.
- **Task 3:** An interactive Savings Planner program.

Existing Stage 1 and Stage 2 programs remain supported.

## Setup and Usage

Requirements: Python 3, `llvmlite`, LLVM (`llc`), and Clang.

```bash
python3 -m pip install llvmlite
```

Generate LLVM IR:

```bash
python3 compiler.py input.txt output.ll
```

Print the AST:

```bash
python3 compiler.py --ast input.txt
```

Enable optimization:

```bash
python3 compiler.py input.txt output.ll --optimize
```

Print the optimized AST:

```bash
python3 compiler.py --optimize --ast input.txt
```

The `--optimize` flag can appear anywhere in the command.

Compilation errors are printed to stderr in the format:

```text
compilation error: line L:C: message
```

Compilation failures return a non-zero exit code and do not create an output file.

---

## Task 1 — New Language Feature: For Loops

I implemented integer-range `for` loops. The syntax is also included in `grammar.ebnf`.

### Syntax and Rules

```text
for i in range(start, stop) {
    statements
}
```

- `start` is inclusive and `stop` is exclusive.
- The counter increases by 1.
- Both bounds must be integer types (`num32` or `num64`).
- The bounds are evaluated once before the loop.
- The loop counter is read-only and scoped to its loop.
- Nested loops and variables declared inside loops are supported.
- If `start >= stop`, the loop executes zero times.

### Example 1: For Loop

```text
num32 mut total{0}

for i in range(0, 4) {
    total := total + i
}

print(total)
exit 0
```

Output:

```text
6
Program exit with result 0
```

### Example 2: Nested Loops and Break

```text
num32 mut visits{0}

for row in range(0, 3) {
    for col in range(0, 5) {
        if col == 2 {
            break
        }

        visits := visits + 1
    }
}

print(visits)
exit 0
```

Output:

```text
6
Program exit with result 0
```

### Bonus: Break

The optional `break` statement immediately exits the innermost `for` or `while` loop. Using `break` outside a loop causes a compilation error.

### LLVM IR Example

Excerpt from the compiler-generated LLVM IR for `tests/stage3_feature_ok/for_range_basic.txt`:

```llvm
  store i32 0, i32* %"k"
  br label %"for.cond"
for.cond:
  %"for.index" = load i32, i32* %"k"
  %".5" = icmp slt i32 %"for.index", 5
  br i1 %".5", label %"for.body", label %"for.end"
for.body:
  %"load_sum" = load i32, i32* %"sum"
  %"load_k" = load i32, i32* %"k"
  %"addtmp" = add i32 %"load_sum", %"load_k"
  store i32 %"addtmp", i32* %"sum"
  br label %"for.step"
for.step:
  %".9" = load i32, i32* %"k"
  %".10" = add i32 %".9", 1
  store i32 %".10", i32* %"k"
  br label %"for.cond"
```

The initial `store` initializes the counter, and `icmp slt` checks whether it is below the upper bound. The conditional branch selects the loop body or the end, while the body performs the calculation. The `for.step` block increments the counter and branches back to `for.cond`, creating the loop's back edge.

The LLVM IR is generated using `llvmlite.ir.IRBuilder`.

### Feature Tests

Valid examples:

- `tests/stage3_feature_ok/for_range_basic.txt`
- `tests/stage3_feature_ok/for_nested.txt`
- `tests/stage3_feature_ok/for_break.txt`

Invalid examples:

- `tests/stage3_feature_err/for_bad_syntax.txt`
- `tests/stage3_feature_err/for_bool_range.txt`
- `tests/stage3_feature_err/for_assign_counter.txt`
- `tests/stage3_feature_err/for_break_outside.txt`

---

## Task 2 — AST Optimizer

The optimizer is implemented in `src/optimizer.py` and runs on the checked AST before LLVM IR generation.

It supports three transformations.

### 1. Unused Variables

Removes declarations that are never read, together with unnecessary pure assignments. The pass repeats until no more unused declarations can be removed.

It respects variable scopes and shadowing. Expressions containing side effects, such as `read()` or function calls, are preserved.

### 2. Unused Functions

Removes functions that are unreachable from the main program, including chains of unused functions.

Structure member methods are conservatively preserved.

### 3. Function Inlining

Replaces a function called exactly once with its body at the call site.

Parameters become uniquely renamed local variables initialized with the arguments, and the return expression replaces the function call.

Recursive functions are never inlined.

The implementation supports simple functions with a single return expression and direct call sites such as `print(f(...))`, `exit f(...)`, or variable initialization.

More complex bodies, including early returns inside conditions, are left unchanged.

### LLVM IR Before and After Inlining

Example: `tests/stage3_opt/inlining_a.txt`.

Before optimization:

```llvm
  %"call_twice" = call i32 @"user_twice"(i32 6)
  %".2" = bitcast [4 x i8]* @"text_1" to i8*
  %".3" = call i32 (i8*, ...) @"printf"(i8* %".2", i32 %"call_twice")
```

After optimization:

```llvm
  %"__inlined_twice_1_x" = alloca i32
  store i32 6, i32* %"__inlined_twice_1_x"
  %"load___inlined_twice_1_x" = load i32, i32* %"__inlined_twice_1_x"
  %"load___inlined_twice_1_x.1" = load i32, i32* %"__inlined_twice_1_x"
  %"addtmp" = add i32 %"load___inlined_twice_1_x", %"load___inlined_twice_1_x.1"
  %".3" = bitcast [4 x i8]* @"text_1" to i8*
  %".4" = call i32 (i8*, ...) @"printf"(i8* %".3", i32 %"addtmp")
```

The function call is replaced by the renamed parameter and arithmetic instructions. The unused function definition is removed. Both versions print the same output.

In this example, LLVM IR decreased from 35 to 28 lines.

### Optimizer Tests

Six test programs are stored in `tests/stage3_opt/`:

- `unused_variables_a.txt`
- `unused_variables_b.txt`
- `unused_functions_a.txt`
- `unused_functions_b.txt`
- `inlining_a.txt`
- `inlining_b.txt`

Each has an expected optimized AST (`.ast`) and output (`.expected`). The test script checks output with and without optimization and compares the optimized AST.

---

## Task 3 — Real Program: Savings Planner

1. `programs/savings_planner.txt` is an interactive savings calculator.
2. It asks the user how many deposits they want to enter.
3. It reads the number of deposits using `read()`.
4. It uses a `Savings` structure to store the total.
5. The structure has an `add()` member function.
6. A Stage 3 `for` loop processes each deposit.
7. Each deposit is entered using `read()`.
8. The program prints the running total after every deposit.
9. A separate `twice()` function calculates a doubled savings goal.
10. Finally, it prints the saved amount and doubled goal.

### Recorded Sessions

Session 1 uses three deposits:

```text
programs/savings_planner.in
programs/savings_planner.expected
```

Session 2 uses zero deposits:

```text
programs/savings_planner_zero.in
programs/savings_planner_zero.expected
```

Both sessions are executed by the test script.

### Native Compilation

Compile the program to a native executable using `llc` and `clang`:

```bash
python3 compiler.py programs/savings_planner.txt savings.ll
llc -filetype=obj savings.ll -o savings.o
clang savings.o -o savings_planner
```

Run interactively:

```bash
./savings_planner
```

Run recorded session 1:

```bash
./savings_planner < programs/savings_planner.in
```

Run recorded session 2:

```bash
./savings_planner < programs/savings_planner_zero.in
```

Compile the optimized version:

```bash
python3 compiler.py programs/savings_planner.txt savings_opt.ll --optimize
llc -filetype=obj savings_opt.ll -o savings_opt.o
clang savings_opt.o -o savings_planner_opt
```

---

## Testing

Run all test suites:

```bash
python3 run_tests.py
python3 run_stage2_tests.py
python3 run_stage3_tests.py
```

Verified results in Ubuntu:

| Test Suite | Result |
|---|---|
| Stage 1 | 35/35 PASS |
| Stage 2 | 37/37 PASS |
| Stage 3 | 110/110 PASS |
| **Total** | **182/182 PASS** |

Stage 3 tests include valid and invalid feature programs, optimizer AST comparisons, output equivalence with and without `--optimize`, Stage 2 regression tests, and recorded program sessions.

Native compilation and interactive execution were also verified using `llc` and `clang`.

## Project Structure

```text
compiler.py
src/
    engine.py
    stage1_frontend.py
    optimizer.py
grammar.ebnf
README.md
run_tests.py
run_stage2_tests.py
run_stage3_tests.py
tests/
    ok/
    err/
    stage2_ok/
    stage2_err/
    stage3_feature_ok/
    stage3_feature_err/
    stage3_opt/
programs/
    savings_planner.txt
    savings_planner.in
    savings_planner.expected
    savings_planner_zero.in
    savings_planner_zero.expected
ai_usage_3.txt
```

## Submission

Stage 3 is developed in the `stage3` branch created from `stage2`.

The pull request targets `main` and must be marked ready for review, with `vovaskochko` requested as reviewer. The PR must not be merged before review.

The Moodle submission includes the pull request link and `ai_usage_3.txt`.

Generated LLVM IR files, object files, executables, and temporary files must not be committed.
