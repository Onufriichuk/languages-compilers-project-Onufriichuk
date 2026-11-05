"""Conservative, semantics-preserving transformations of the checked Stage 3 AST.

The optimizer deliberately leaves unfamiliar / effectful shapes alone rather than
changing evaluation order. It operates on typed, scope-resolved nodes.
"""
from collections import Counter
from copy import deepcopy
from . import engine as e

_SKIP = {'decl', 'method', 'struct_def', 'owner', 'type', 'type_name', 'mutable_path',
         'field_index', 'loop_decl', 'generated_decl', 'generated_struct', 'function',
         'callable_member', 'temporary', 'is_lvalue', 'mutating', 'same_object_calls',
         'member_calls', 'method_map', 'storage', 'params', 'captures'}

def walk(node):
    if node is None:
        return
    if isinstance(node, list):
        for item in node:
            yield from walk(item)
    elif isinstance(node, e.Node):
        yield node
        for key, value in vars(node).items():
            if key not in _SKIP and key not in {'line', 'column', 'name', 'result_type', 'op', 'fields', 'mutable'}:
                if isinstance(value, (e.Node, list)):
                    yield from walk(value)

def effects(node):
    return any(isinstance(n, (e.CallNode, e.MemberCallNode)) for n in walk(node))

def statements(container):
    return container.statements

def blocks(root):
    yield root
    for n in walk(root):
        if n is not root and isinstance(n, e.BlockNode):
            yield n

def all_expr_roots(tree):
    for fn in tree.functions:
        yield fn.body
    for st in tree.structs:
        for method in st.methods:
            yield method.body
    yield tree

def remove_unused_variables(tree):
    changed = True
    while changed:
        changed = False
        reads = Counter(n.decl for n in walk(tree) if isinstance(n, (e.VarNode, e.FieldAccessNode)) and hasattr(n, 'decl'))
        # Assignments to a variable are writes, not reads.
        # A dead variable with a side-effecting assignment must keep its storage.
        protected = {getattr(n.target, 'decl', None) for n in walk(tree)
                     if isinstance(n, e.AssignNode) and isinstance(n.target, e.VarNode)
                     and effects(n.value)}
        for n in walk(tree):
            if isinstance(n, e.AssignNode) and isinstance(n.target, e.VarNode) and hasattr(n.target, 'decl'):
                reads[n.target.decl] -= 1
        for root in [tree] + [f.body for f in tree.functions] + [m.body for st in tree.structs for m in st.methods]:
            for block in blocks(root):
                sequence = block.statements
                retained = []
                for stmt in sequence:
                    if isinstance(stmt, e.DeclNode) and reads[stmt] <= 0 and stmt not in protected and not effects(stmt.init):
                        changed = True
                        continue
                    if isinstance(stmt, e.AssignNode) and isinstance(stmt.target, e.VarNode):
                        decl = getattr(stmt.target, 'decl', None)
                        if decl is not None and reads[decl] <= 0 and not effects(stmt.value):
                            changed = True
                            continue
                    retained.append(stmt)
                sequence[:] = retained
    return tree

def remove_unused_functions(tree):
    # Reachability from main and all member functions (members can be invoked dynamically).
    known = {f.name: f for f in tree.functions}
    reachable = set()
    roots = [tree] + [m.body for st in tree.structs for m in st.methods]
    # Program traversal includes function bodies, so visit statements separately.
    pending = list(tree.statements) + [tree.exit_node]
    for st in tree.structs:
        for method in st.methods:
            pending.append(method.body)
    while pending:
        part = pending.pop()
        for n in walk(part):
            if isinstance(n, e.CallNode) and n.name in known and n.name not in reachable:
                reachable.add(n.name)
                pending.append(known[n.name].body)
    tree.functions[:] = [f for f in tree.functions if f.name in reachable]
    return tree

def pure(node):
    return not effects(node)

def inline_once(tree):
    calls = Counter(n.name for n in walk(tree) if isinstance(n, e.CallNode))
    # Count calls only in live function bodies or the main program.
    live_calls = Counter()
    for part in [*tree.statements, tree.exit_node, *(f.body for f in tree.functions),
                 *(m.body for st in tree.structs for m in st.methods)]:
        live_calls.update(n.name for n in walk(part) if isinstance(n, e.CallNode))
    eligible = {}
    for f in tree.functions:
        if live_calls[f.name] != 1 or f.body.statements or f.body.exit_node is None:
            continue
        if any(isinstance(n, e.CallNode) and n.name == f.name for n in walk(f.body)):
            continue
        # Do not move side effects from the callee's result into an earlier position.
        if not pure(f.body.exit_node.value):
            continue
        eligible[f.name] = f
    nonce = 0
    done = set()

    def transform(seq, exit_node=None):
        nonlocal nonce
        new = []
        for stmt in list(seq) + ([exit_node] if exit_node else []):
            if stmt is None:
                continue
            expr = (stmt.init if isinstance(stmt, e.DeclNode) else
                    stmt.value if isinstance(stmt, (e.PrintNode, e.ExitNode)) else None)
            if isinstance(expr, e.CallNode) and expr.name in eligible and expr.name not in done:
                f = eligible[expr.name]
                if len(expr.args) == len(f.params):
                    nonce += 1
                    rename = {}
                    prefix = f'__inlined_{f.name}_{nonce}_'
                    locals_ = []
                    for param, arg in zip(f.params, expr.args):
                        unique = prefix + param.name
                        rename[param.name] = unique
                        locals_.append(e.DeclNode(arg.line, arg.column, unique, param.type_name, False, arg))
                    result = deepcopy(f.body.exit_node.value)
                    for n in walk(result):
                        if isinstance(n, e.VarNode) and n.name in rename:
                            n.name = rename[n.name]
                    if isinstance(stmt, e.DeclNode):
                        stmt.init = result
                    else:
                        stmt.value = result
                    new.extend(locals_)
                    done.add(f.name)
            new.append(stmt)
        if exit_node is not None:
            seq[:] = new[:-1]
            return new[-1]
        seq[:] = new

    tree.exit_node = transform(tree.statements, tree.exit_node)
    for fn in tree.functions:
        fn.body.exit_node = transform(fn.body.statements, fn.body.exit_node)
    for st in tree.structs:
        for method in st.methods:
            method.body.exit_node = transform(method.body.statements, method.body.exit_node)
    return tree

def optimize(tree):
    # Structural rewrites invalidate symbol bindings. Refresh after each transformation.
    e.SemanticChecker().check(tree)
    remove_unused_functions(tree)
    inline_once(tree)
    e.SemanticChecker().check(tree)
    remove_unused_variables(tree)
    remove_unused_functions(tree)
    e.SemanticChecker().check(tree)
    return tree
