\
\
\
\

import re
import sys
from difflib import SequenceMatcher
from bisect import bisect_right
from pathlib import Path
from src import engine
from src import stage1_frontend
from llvmlite import ir
import llvmlite.binding as llvm


def normalize(text):
\
\
\
\

    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|:=|->|==|!=|\d+|\n|[^\s]', text)
    result = []
    current = []
    brace_kind = []
    parens = 0
    for index, token in enumerate(tokens):
        if token == '\n':
            if current and parens == 0 and (not brace_kind or brace_kind[-1] == 'block'):
                result.append(' '.join(current))
                current=[]
            continue
        if token.startswith('"'):
            current.append(token)
            continue
        token = {'num32':'i32', 'num64':'i64'}.get(token,token)
        if token == '(':
            parens += 1
        elif token == ')':
            parens -= 1
        if token == '{':


            prefix = current[:]
            structural = (not brace_kind and prefix and prefix[0] in {'if','else','while','struct','fn'}) or (prefix and prefix[0] in {'if','else','while','struct','fn'} and not any(k == 'init' for k in brace_kind)) or (not prefix and (not brace_kind or brace_kind[-1] == 'block'))
            if structural:
                if current:
                    result.append(' '.join(current))
                    current=[]
                result.append('{')
                brace_kind.append('block')
            else:
                brace_kind.append('init')
                current.append('{')
        elif token == '}':
            if not brace_kind:
                current.append('}')
                continue
            kind = brace_kind.pop()
            if kind == 'block':
                if current:
                    result.append(' '.join(current))
                    current=[]
                result.append('}')
            else:
                current.append('}')
        elif token == ';' and parens == 0 and (not brace_kind or brace_kind[-1] == 'block'):
            if current:
                result.append(' '.join(current))
                current=[]
        else:
            current.append(token)
    if current:
        result.append(' '.join(current))
    if not any(line.split(' ',1)[0] == 'exit' for line in result if line):
        result.append('exit 0')
    return '\n'.join(result)+'\n'





_MAP_TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|:=|->|==|!=|\d+|[^\s]')


def _located_tokens(source):
    line_starts = [0]
    for m in re.finditer('\n', source):
        line_starts.append(m.end())
    located = []
    for m in _MAP_TOKEN_RE.finditer(source):
        line_index = bisect_right(line_starts, m.start()) - 1
        located.append((m.group(), line_index + 1, m.start() - line_starts[line_index] + 1))
    return located


def remap_diagnostic(message, original, normalized):
    position = re.match(r'line (\d+):(\d+): (.*)', message, re.S)
    if not position:
        return message
    err_line, err_col = int(position[1]), int(position[2])
    before = _located_tokens(original)
    after = _located_tokens(normalized)


    left = [('i32' if t[0] == 'num32' else 'i64' if t[0] == 'num64' else t[0]) for t in before]
    right = [t[0] for t in after]
    matches = {}
    for match in SequenceMatcher(None, left, right, autojunk=False).get_matching_blocks():
        for offset in range(match.size):
            matches[match.b + offset] = match.a + offset

    exact = next((idx for idx, (_, line, col) in enumerate(after) if line == err_line and col == err_col), None)
    if exact is None:
        exact = next((idx for idx, (_, line, col) in enumerate(after) if line == err_line and col >= err_col), None)
    if exact is None or exact not in matches:
        return message
    _, real_line, real_col = before[matches[exact]]
    return f'line {real_line}:{real_col}: {position[3]}'

def backend_ast(source):
    tokens = engine.lex(source.encode())
    return engine.Parser(tokens).parse_program()


def codegen(tree):
    checker = engine.SemanticChecker()
    checker.check(tree)
    module = ir.Module(name='stage2')
    module.triple = llvm.get_default_triple()
    main = ir.Function(module, ir.FunctionType(engine.I32, []), name='main')
    builder = ir.IRBuilder(main.append_basic_block('entry'))
    printf = ir.Function(module, ir.FunctionType(engine.I32, [ir.PointerType(engine.I8)], var_arg=True), name='printf')
    text = b'Program exit with result %lld\n\0'
    fmt_type = ir.ArrayType(engine.I8, len(text))
    fmt = ir.GlobalVariable(module, fmt_type, name='fmt')
    fmt.linkage = 'private'
    fmt.global_constant = True
    fmt.initializer = ir.Constant(fmt_type, bytearray(text))
    engine.CodeGen(module,builder,printf,fmt).generate(tree)
    return str(module)


def main():
    if len(sys.argv)!=3:
        print('usage: python3 compiler.py [--ast] input.txt | python3 compiler.py input.txt output.ll',file=sys.stderr)
        return 1
    ast_mode = sys.argv[1] == '--ast'
    source = Path(sys.argv[2] if ast_mode else sys.argv[1])
    destination = None if ast_mode else Path(sys.argv[2])
    if destination:
        destination.unlink(missing_ok=True)
    normalized_source = None
    data = None
    try:
        data=source.read_text(encoding='utf-8')
        if ast_mode:

            try:
                stage1_tree=stage1_frontend.compile_file(str(source))
                print('\n'.join(stage1_frontend.dump_ast(stage1_tree)))
                return 0
            except stage1_frontend.CompilationError:
                if not re.search(r'\b(struct|fn|exit|print|read|while)\b', data):
                    raise
            normalized_source = normalize(data)
            tree=backend_ast(normalized_source)
            print('\n'.join(tree.dump()))
        else:
            normalized_source = normalize(data)
            tree=backend_ast(normalized_source)
            destination.write_text(codegen(tree),encoding='utf-8')
        return 0
    except (engine.CompileError, stage1_frontend.CompilationError) as exc:
        msg=str(exc)
        if isinstance(exc, stage1_frontend.CompilationError):
            msg=f'line {exc.line}:{exc.column}: {exc.message}'
        if normalized_source is not None and data is not None and isinstance(exc, engine.CompileError):
            msg = remap_diagnostic(msg, data, normalized_source)
        if not msg.startswith('line '):
            msg='line 1:1: '+msg
        print('compilation error: '+msg,file=sys.stderr)
    except (OSError, ValueError, TypeError, RuntimeError, IndexError, AssertionError) as exc:
        print(f'compilation error: line 1:1: {type(exc).__name__}: {exc}',file=sys.stderr)
    if destination:
        destination.unlink(missing_ok=True)
    return 1

if __name__=='__main__':
    sys.exit(main())
