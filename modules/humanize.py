"""Stage 1b: Human-fixed Samples -> results/<experiment>/human_fixed.csv.

Each Direct Sample is edited by fixed Edit rules, the way a student touches up code before handing it in.
Terms: GLOSSARY.md (Human-fixed, Edit rule, Edit count). Decisions: issue #8.

- Rules are picked per Sample from a shuffle seeded by sha256(sample_id). Edit count 2 takes the first 2
  applicable rules and Edit count 5 the first 5, so the 5 always include the 2.
- A rule is applicable when it changes the original code. The chosen rules are then applied in CANON order,
  so cut_comments never deletes the debug print and rename runs before the print names a variable.
- Every rule leaves code unchanged unless it can show the edit keeps the program's behaviour.
  The only gate here is "still parses"; the output-equivalence check is #11.
"""
import builtins
import hashlib
import keyword
import random
import subprocess
from importlib.metadata import version

import libcst as cst

from .common import ROOT, append_csv, done_ids, read_csv, results_dir

EDIT_COUNTS = (2, 5)
CANON = ["flatten", "fancy", "loops", "rename", "cut_comments", "debug_print", "spacing"]
RESERVED = set(dir(builtins)) | set(keyword.kwlist) | set(keyword.softkwlist)
# Short names students use. Names not listed become their first letter.
SHORT = {
    "result": "ans", "answer": "ans", "res": "ans", "count": "cnt", "counter": "cnt", "total": "tot",
    "index": "i", "idx": "i", "number": "x", "num": "x", "value": "x", "val": "x", "item": "x",
    "numbers": "a", "nums": "a", "values": "a", "arr": "a", "array": "a", "items": "a",
    "current": "cur", "temp": "tmp", "left": "l", "right": "r", "length": "n", "size": "n",
}
_PASS = cst.SimpleStatementLine([cst.Pass()])
_ATOMS = (cst.Name, cst.Integer, cst.Float, cst.SimpleString, cst.Call, cst.Subscript, cst.Attribute)


# ---------- tree helpers ----------

def _code(node):
    return cst.Module([]).code_for_node(node)


def _targets(node):
    """Names bound by an assignment target (Name, or Names inside a Tuple/List)."""
    if isinstance(node, cst.Name):
        return [node.value]
    if isinstance(node, (cst.Tuple, cst.List)):
        return [n for e in node.elements for n in _targets(e.value)]
    if isinstance(node, cst.StarredElement):
        return _targets(node.value)
    return []


class _Refs(cst.CSTVisitor):
    """Variable references: every Name except attribute names (obj.x) and call keywords (f(x=1))."""

    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        self.names.append(node.value)

    def visit_Attribute(self, node):
        node.value.visit(self)
        return False

    def visit_Arg(self, node):
        node.value.visit(self)
        return False


def _refs(node):
    v = _Refs()
    node.visit(v)
    return v.names


class _Bound(cst.CSTVisitor):
    """Names (re)bound anywhere inside a node."""

    def __init__(self):
        self.names = set()

    def visit_AssignTarget(self, node):
        self.names.update(_targets(node.target))

    def visit_AugAssign(self, node):
        self.names.update(_targets(node.target))

    def visit_AnnAssign(self, node):
        self.names.update(_targets(node.target))

    def visit_For(self, node):
        self.names.update(_targets(node.target))

    def visit_CompFor(self, node):
        self.names.update(_targets(node.target))

    def visit_NamedExpr(self, node):
        self.names.update(_targets(node.target))

    def visit_AsName(self, node):
        self.names.update(_targets(node.name))

    def visit_Param(self, node):
        self.names.add(node.name.value)

    def visit_FunctionDef(self, node):
        self.names.add(node.name.value)

    def visit_ClassDef(self, node):
        self.names.add(node.name.value)

    def visit_ImportAlias(self, node):
        if node.asname is None:
            self.names.add(_code(node.name).split(".")[0])


def _bound(node):
    v = _Bound()
    node.visit(v)
    return v.names


def _has(node, *types):
    found = []

    class V(cst.CSTVisitor):
        def on_visit(self, n):
            if isinstance(n, types):
                found.append(n)
            return not found

    node.visit(V())
    return bool(found)


def _method_called(node, name):
    """True if `name.<anything>` appears in node (e.g. arr.append), a sign the object is mutated."""
    hits = []

    class V(cst.CSTVisitor):
        def visit_Attribute(self, n):
            if isinstance(n.value, cst.Name) and n.value.value == name:
                hits.append(n)

    node.visit(V())
    return bool(hits)


class _InDebugFString(cst.CSTTransformer):
    """Tracks whether we are inside f"{expr=}", which prints expr's source text, so it must not change."""
    debug = 0

    def visit_FormattedStringExpression(self, node):
        self.debug += node.equal is not None

    def leave_FormattedStringExpression(self, original, updated):
        self.debug -= original.equal is not None
        return updated


def _parens(expr):
    return expr if isinstance(expr, _ATOMS) or expr.lpar else expr.with_changes(
        lpar=[cst.LeftParen()], rpar=[cst.RightParen()])


def _block(body):
    """Statements of a For/If body as a list, whether it is indented or a one-line suite."""
    if isinstance(body, cst.IndentedBlock):
        return list(body.body)
    return [cst.SimpleStatementLine(body=body.body)]


# ---------- rule: flatten ----------

def _is_main_guard(stmt):
    if not (isinstance(stmt, cst.If) and stmt.orelse is None and isinstance(stmt.test, cst.Comparison)):
        return False
    t = stmt.test
    if len(t.comparisons) != 1 or not isinstance(t.comparisons[0].operator, cst.Equal):
        return False
    sides = {_code(t.left).strip(), _code(t.comparisons[0].comparator).strip()}
    return sides in ({"__name__", '"__main__"'}, {"__name__", "'__main__'"})


def _pure(e):
    """No side effects and cheap to evaluate twice: safe to duplicate or reorder when inlining."""
    if isinstance(e, (cst.Name, cst.Integer, cst.Float, cst.SimpleString)):
        return True
    if isinstance(e, cst.Attribute):
        return _pure(e.value)
    if isinstance(e, cst.Subscript):
        return _pure(e.value) and all(
            isinstance(s.slice, cst.Index) and _pure(s.slice.value) for s in e.slice)
    if isinstance(e, cst.UnaryOperation):
        return _pure(e.expression)
    if isinstance(e, cst.BinaryOperation):
        return _pure(e.left) and _pure(e.right)
    return False


def _tiny_helpers(module):
    """Module-level `def f(a, b): return <expr>` whose every use is a call with pure positional args."""
    bound = _bound(module)
    refs = _refs(module)
    helpers = {}
    for s in module.body:
        if not (isinstance(s, cst.FunctionDef) and not s.decorators and s.asynchronous is None):
            continue
        p = s.params
        if p.star_arg is not cst.MaybeSentinel.DEFAULT or p.kwonly_params or p.star_kwarg or p.posonly_params:
            continue
        if any(x.default or x.star not in ("", cst.MaybeSentinel.DEFAULT) for x in p.params):
            continue
        body = s.body.body if isinstance(s.body, cst.IndentedBlock) else ()
        if not (len(body) == 1 and isinstance(body[0], cst.SimpleStatementLine) and len(body[0].body) == 1
                and isinstance(body[0].body[0], cst.Return) and body[0].body[0].value is not None):
            continue
        expr = body[0].body[0].value
        params = [x.name.value for x in p.params]
        free = set(_refs(expr)) - set(params)
        # Only params and builtins nobody shadows; nothing that binds its own names.
        if not free <= RESERVED - bound or _has(expr, cst.Lambda, cst.ListComp, cst.SetComp, cst.DictComp,
                                                 cst.GeneratorExp, cst.NamedExpr, cst.Yield, cst.Await):
            continue
        helpers[s.name.value] = (params, expr)

    calls = {name: 0 for name in helpers}

    class Calls(_InDebugFString):
        def visit_Call(self, n):
            f = n.func
            if not self.debug and isinstance(f, cst.Name) and f.value in helpers and len(n.args) == len(helpers[f.value][0]) \
                    and all(a.keyword is None and a.star == "" and _pure(a.value) for a in n.args):
                calls[f.value] += 1

    module.visit(Calls())
    return {k: v for k, v in helpers.items() if calls[k] and refs.count(k) == 1 + calls[k]}


class _Substitute(cst.CSTTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def leave_Name(self, original, updated):
        return self.mapping.get(updated.value, updated)

    def leave_Attribute(self, original, updated):
        return updated.with_changes(attr=original.attr)

    def leave_Arg(self, original, updated):
        return updated.with_changes(keyword=original.keyword)


class _Flatten(cst.CSTTransformer):
    def __init__(self, module):
        self.helpers = _tiny_helpers(module)

    def leave_Call(self, original, updated):
        f = updated.func
        if isinstance(f, cst.Name) and f.value in self.helpers:
            params, expr = self.helpers[f.value]
            mapping = {p: _parens(a.value) for p, a in zip(params, updated.args)}
            return _parens(expr.visit(_Substitute(mapping)))
        return updated

    def leave_FunctionDef(self, original, updated):
        return cst.RemoveFromParent() if original.name.value in self.helpers else updated

    def leave_Module(self, original, updated):
        body = []
        for s in updated.body:
            if _is_main_guard(s):
                inner = _block(s.body)
                inner[0] = inner[0].with_changes(leading_lines=[*s.leading_lines, *inner[0].leading_lines])
                body.extend(inner)
            else:
                body.append(s)
        return updated.with_changes(body=body)


def rule_flatten(module, rng):
    return module.visit(_Flatten(module))


# ---------- rule: fancy ----------

def _list_names(module):
    """Names only ever assigned list-like values, so indexing them by position is safe."""
    good, bad = set(), set()

    def listy(v):
        if isinstance(v, (cst.List, cst.ListComp)):
            return True
        if isinstance(v, cst.Call):
            f = v.func
            return (isinstance(f, cst.Name) and f.value in ("list", "sorted")) or (
                isinstance(f, cst.Attribute) and f.attr.value == "split")
        if isinstance(v, cst.BinaryOperation) and isinstance(v.operator, cst.Multiply):
            return isinstance(v.left, cst.List) or isinstance(v.right, cst.List)
        return False

    class V(_Bound):
        def visit_Assign(self, n):
            for t in n.targets:
                if isinstance(t.target, cst.Name):
                    (good if listy(n.value) else bad).add(t.target.value)
            return False

        def visit_AugAssign(self, n):
            return False  # arr += [x] keeps a list

    v = V()
    module.visit(v)
    return good - bad - v.names


def _print_args(fs):
    """f"a {x} b {y}" -> ["a", x, "b", y] when print() of those gives the exact same text, else None."""
    if fs.start not in ('f"', "f'"):
        return None
    q = fs.end
    parts = list(fs.parts)
    items = []
    for i, p in enumerate(parts):
        if isinstance(p, cst.FormattedStringExpression):
            if p.conversion or p.format_spec or p.equal:
                return None
            items.append(p.expression)
            continue
        t = p.value
        if "{{" in t or "}}" in t:
            return None
        before, after = i > 0, i < len(parts) - 1  # an expression sits next to this text
        if (before and not t.startswith(" ")) or (after and not t.endswith(" ")):
            return None
        t = t[1 if before else 0: len(t) - (1 if after else 0)]
        if t == "":
            if not (before and after and p.value == " "):
                return None
            continue
        items.append(cst.SimpleString(q + t + q))
    return items


class _Fancy(cst.CSTTransformer):
    def __init__(self, module):
        self.lists = _list_names(module)
        self.used = _bound(module) | set(_refs(module))
        self.in_class = 0

    def visit_ClassDef(self, node):
        self.in_class += 1

    def leave_ClassDef(self, original, updated):
        self.in_class -= 1
        return updated

    def leave_Param(self, original, updated):
        if updated.annotation is None:
            return updated
        return updated.with_changes(annotation=None, equal=cst.MaybeSentinel.DEFAULT)

    def leave_FunctionDef(self, original, updated):
        return updated.with_changes(returns=None)

    def leave_AnnAssign(self, original, updated):
        # Class-level annotations can be dataclass fields; bare `x: int` declares, so leave both.
        if self.in_class or updated.value is None:
            return updated
        return cst.Assign(targets=[cst.AssignTarget(updated.target)], value=updated.value)

    def leave_Call(self, original, updated):
        f = updated.func
        if not (isinstance(f, cst.Name) and f.value == "print" and len(updated.args) == 1):
            return updated
        a = updated.args[0]
        if a.keyword or a.star or not isinstance(a.value, cst.FormattedString):
            return updated
        items = _print_args(a.value)
        return updated if items is None else updated.with_changes(args=[cst.Arg(i) for i in items])

    def _fresh(self):
        for n in ["i", "j", "k", *(f"i{d}" for d in range(2, 99))]:
            if n not in self.used:
                self.used.add(n)
                return n

    def leave_For(self, original, updated):
        it, tgt = updated.iter, updated.target
        if not (isinstance(it, cst.Call) and isinstance(it.func, cst.Name) and it.func.value in ("enumerate", "zip")
                and isinstance(updated.body, cst.IndentedBlock) and updated.asynchronous is None):
            return updated
        if not all(a.keyword is None and a.star == "" and isinstance(a.value, cst.Name) for a in it.args):
            return updated
        seqs = [a.value.value for a in it.args]
        names = _targets(tgt) if isinstance(tgt, cst.Tuple) else []
        if not (isinstance(tgt, cst.Tuple) and all(isinstance(e.value, cst.Name) for e in tgt.elements)):
            return updated
        body_bound = _bound(updated.body)
        if any(s not in self.lists or s in body_bound or _method_called(updated.body, s) for s in seqs):
            return updated
        if it.func.value == "enumerate":
            if len(seqs) != 1 or len(names) != 2:
                return updated
            idx, pairs = names[0], [(names[1], seqs[0])]
            rng_expr = f"range(len({seqs[0]}))"
        else:
            if len(seqs) != len(names) or not seqs:
                return updated
            idx, pairs = self._fresh(), list(zip(names, seqs))
            lens = ", ".join(f"len({s})" for s in seqs)
            rng_expr = f"range({lens})" if len(seqs) == 1 else f"range(min({lens}))"
        loads = [cst.parse_statement(f"{n} = {s}[{idx}]\n") for n, s in pairs]
        return updated.with_changes(
            target=cst.Name(idx), iter=cst.parse_expression(rng_expr),
            body=updated.body.with_changes(body=[*loads, *updated.body.body]))


def rule_fancy(module, rng):
    return module.visit(_Fancy(module))


# ---------- rule: loops ----------

class _Uses(cst.CSTVisitor):
    """References to `name` outside `skip`, ignoring loops that rebind `name` before using it."""

    def __init__(self, name, skip):
        self.name, self.skip, self.depth, self.n = name, skip, 0, 0

    def _rebinds(self, node):
        return node is self.skip or self.name in _targets(node.target)

    def visit_For(self, node):
        self.depth += self._rebinds(node)

    def leave_For(self, node):
        self.depth -= self._rebinds(node)

    def visit_ListComp(self, node):
        if node is self.skip:
            self.depth += 1

    def leave_ListComp(self, node):
        if node is self.skip:
            self.depth -= 1

    def visit_Name(self, node):
        self.n += node.value == self.name and self.depth == 0


def _uses_outside(module, name, skip):
    v = _Uses(name, skip)
    module.visit(v)
    return v.n


def _stable(e, body):
    """A while-condition bound that cannot change while the loop body runs."""
    bound = _bound(body)
    if isinstance(e, cst.Integer):
        return True
    if isinstance(e, cst.Name):
        return e.value not in bound
    if isinstance(e, cst.BinaryOperation):
        return _stable(e.left, body) and _stable(e.right, body)
    if isinstance(e, cst.Call) and isinstance(e.func, cst.Name) and e.func.value == "len" and len(e.args) == 1:
        a = e.args[0].value
        return isinstance(a, cst.Name) and a.value not in bound and not _method_called(body, a.value) \
            and not _has(body, cst.Del)
    return False


class _Loops(cst.CSTTransformer):
    def __init__(self, module):
        self.module = module
        self.in_class = 0

    def visit_ClassDef(self, node):
        self.in_class += 1

    def leave_ClassDef(self, original, updated):
        self.in_class -= 1
        return updated

    def leave_For(self, original, updated):
        """for x in range(a, b, s) -> x = a / while x < b: ... x += s"""
        it = original.iter
        if not (isinstance(original.target, cst.Name) and isinstance(it, cst.Call)
                and isinstance(it.func, cst.Name) and it.func.value == "range" and 1 <= len(it.args) <= 3
                and all(a.keyword is None and a.star == "" for a in it.args)
                and original.orelse is None and original.asynchronous is None):
            return updated
        x = original.target.value
        args = [a.value for a in it.args]
        start, stop = (cst.Integer("0"), args[0]) if len(args) == 1 else (args[0], args[1])
        step = args[2] if len(args) == 3 else cst.Integer("1")
        if not (isinstance(step, cst.Integer) and int(step.value, 0) > 0):
            return updated
        body = original.body
        if (_has(body, cst.Continue, cst.FunctionDef, cst.Lambda) or x in _bound(body) or x in _refs(stop)
                or not _stable(stop, body) or _uses_outside(self.module, x, original)):
            return updated
        init = cst.parse_statement(f"{x} = {_code(start)}\n").with_changes(leading_lines=updated.leading_lines)
        inc = cst.parse_statement(f"{x} += {step.value}\n")
        loop = cst.While(test=cst.parse_expression(f"{x} < {_code(stop)}"),
                         body=cst.IndentedBlock(body=[*_block(updated.body), inc]))
        return cst.FlattenSentinel([init, loop])

    def leave_SimpleStatementLine(self, original, updated):
        """name = [e for x in it if c] -> name = [] / for x in it: if c: name.append(e)"""
        if self.in_class or len(original.body) != 1 or not isinstance(original.body[0], cst.Assign):
            return updated
        a = original.body[0]
        if len(a.targets) != 1 or not isinstance(a.targets[0].target, cst.Name):
            return updated
        comp = a.value
        if not (isinstance(comp, cst.ListComp) and comp.for_in.inner_for_in is None
                and comp.for_in.asynchronous is None):
            return updated
        name = a.targets[0].target.value
        cf = comp.for_in
        if name in _refs(comp) or any(_uses_outside(self.module, t, comp) for t in _targets(cf.target)):
            return updated
        inner = cst.SimpleStatementLine([cst.Expr(cst.Call(
            func=cst.Attribute(cst.Name(name), cst.Name("append")), args=[cst.Arg(comp.elt)]))])
        for c in reversed(cf.ifs):
            inner = cst.If(test=c.test, body=cst.IndentedBlock([inner]))
        init = cst.parse_statement(f"{name} = []\n").with_changes(leading_lines=updated.leading_lines)
        return cst.FlattenSentinel([init, cst.For(target=cf.target, iter=cf.iter, body=cst.IndentedBlock([inner]))])

    def leave_FunctionDef(self, original, updated):
        """if c: ... return x / rest -> if c: ... return x / else: rest"""
        if not isinstance(updated.body, cst.IndentedBlock):
            return updated
        body = list(updated.body.body)
        for i, s in enumerate(body[:-1]):
            if isinstance(s, cst.If) and s.orelse is None and isinstance(s.body, cst.IndentedBlock):
                last = s.body.body[-1]
                if isinstance(last, cst.SimpleStatementLine) and isinstance(last.body[-1], cst.Return):
                    body[i:] = [s.with_changes(orelse=cst.Else(body=cst.IndentedBlock(body[i + 1:])))]
                    return updated.with_changes(body=updated.body.with_changes(body=body))
        return updated


def rule_loops(module, rng):
    return module.visit(_Loops(module))


# ---------- rule: rename ----------

class _Rename(cst.CSTTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def leave_Name(self, original, updated):
        return updated.with_changes(value=self.mapping.get(updated.value, updated.value))


def rule_rename(module, rng):
    attrs, keywords, protected, every = set(), set(), set(), set()

    class V(cst.CSTVisitor):
        def visit_Name(self, n):
            every.add(n.value)

        def visit_Attribute(self, n):
            attrs.add(n.attr.value)

        def visit_Arg(self, n):
            if n.keyword:
                keywords.add(n.keyword.value)

        def visit_FunctionDef(self, n):
            protected.add(n.name.value)

        def visit_ClassDef(self, n):
            protected.add(n.name.value)

        def visit_Import(self, n):
            protected.update(_refs(n))

        def visit_ImportFrom(self, n):
            protected.update(_refs(n))

        def visit_Global(self, n):
            protected.update(i.name.value for i in n.names)

        def visit_Nonlocal(self, n):
            protected.update(i.name.value for i in n.names)

        def visit_FormattedStringExpression(self, n):
            if n.equal is not None:
                protected.update(_refs(n.expression))

    module.visit(V())
    # ponytail: one mapping per module, so names in different functions collide into a2, x3.
    # Scope-aware renaming (libcst ScopeProvider) if the hand check (#10) says it looks unnatural.
    rename = sorted(n for n in _bound(module) - protected - attrs - keywords - RESERVED - {"self", "cls"}
                    if not n.startswith("__") and (n in SHORT or len(n) > 3))
    taken = every | RESERVED
    mapping = {}
    for old in rename:
        stem = old.lstrip("_")
        base = SHORT.get(old) or (stem[0].lower() if stem and stem[0].isalpha() else "v")
        new, d = base, 2
        while new in taken:
            new, d = f"{base}{d}", d + 1
        taken.add(new)
        mapping[old] = new
    return module.visit(_Rename(mapping))


# ---------- rule: cut_comments ----------

def _no_docstrings(stmts):
    out = [s for s in stmts if not (
        isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1 and isinstance(s.body[0], cst.Expr)
        and isinstance(s.body[0].value, (cst.SimpleString, cst.ConcatenatedString)))]
    return out


class _CutComments(cst.CSTTransformer):
    def leave_EmptyLine(self, original, updated):
        return cst.RemoveFromParent() if updated.comment else updated

    def leave_TrailingWhitespace(self, original, updated):
        return updated.with_changes(whitespace=cst.SimpleWhitespace(""), comment=None) if updated.comment else updated

    def leave_IndentedBlock(self, original, updated):
        return updated.with_changes(body=_no_docstrings(updated.body) or [_PASS])

    def leave_Module(self, original, updated):
        return updated.with_changes(body=_no_docstrings(updated.body))


def rule_cut_comments(module, rng):
    return module.visit(_CutComments())


# ---------- rule: debug_print ----------

class _DebugPrint(cst.CSTTransformer):
    """Puts `# print(<var>)` after the k-th simple assignment that has a statement after it."""

    def __init__(self, k):
        self.k, self.seen = k, 0

    def _walk(self, body):
        body = list(body)
        for i, s in enumerate(body[:-1]):
            if not (isinstance(s, cst.SimpleStatementLine) and len(s.body) == 1):
                continue
            a = s.body[0]
            t = a.targets[0].target if isinstance(a, cst.Assign) and len(a.targets) == 1 else getattr(a, "target", None)
            if not (isinstance(a, (cst.Assign, cst.AugAssign)) and isinstance(t, cst.Name)):
                continue
            if self.seen == self.k:
                line = cst.EmptyLine(comment=cst.Comment(f"# print({t.value})"))
                body[i + 1] = body[i + 1].with_changes(leading_lines=[*body[i + 1].leading_lines, line])
            self.seen += 1
        return body

    def leave_IndentedBlock(self, original, updated):
        return updated.with_changes(body=self._walk(updated.body))

    def leave_Module(self, original, updated):
        return updated.with_changes(body=self._walk(updated.body))


def rule_debug_print(module, rng):
    count = _DebugPrint(-1)
    module.visit(count)
    return module.visit(_DebugPrint(rng.randrange(count.seen))) if count.seen else module


# ---------- rule: spacing ----------

class _Spacing(_InDebugFString):
    def __init__(self, rng):
        self.rng = rng

    def leave_AssignTarget(self, original, updated):
        if self.rng.random() < 0.5:
            return updated.with_changes(whitespace_before_equal=cst.SimpleWhitespace(""),
                                        whitespace_after_equal=cst.SimpleWhitespace(""))
        return updated

    def leave_BinaryOperation(self, original, updated):
        op = updated.operator
        if not self.debug and self.rng.random() < 0.5 and isinstance(op.whitespace_before, cst.SimpleWhitespace) \
                and isinstance(op.whitespace_after, cst.SimpleWhitespace):
            return updated.with_changes(operator=op.with_changes(
                whitespace_before=cst.SimpleWhitespace(""), whitespace_after=cst.SimpleWhitespace("")))
        return updated

    def _lines(self, body):
        out = []
        for i, s in enumerate(body):
            lines = list(s.leading_lines)
            r = self.rng.random()
            if i and r < 0.2:
                lines.append(cst.EmptyLine(indent=False))
            elif r < 0.5:
                lines = [ln for ln in lines if ln.comment]  # drop blank lines, keep comment lines
            out.append(s.with_changes(leading_lines=lines))
        return out

    def leave_IndentedBlock(self, original, updated):
        return updated.with_changes(body=self._lines(updated.body))

    def leave_Module(self, original, updated):
        return updated.with_changes(body=self._lines(updated.body))


def rule_spacing(module, rng):
    return module.visit(_Spacing(rng))


# ---------- picking and applying ----------

RULES = {name: globals()[f"rule_{name}"] for name in CANON}


def _apply(rule, module, seed):
    # Each rule gets its own stream, so its random choices don't depend on which rules ran before it.
    return RULES[rule](module, random.Random(f"{seed}:{rule}"))


def edit(code, source_id):
    """{edit_count: (edited code or "", rules applied, status)} for one Direct Sample, plus the seed."""
    seed = hashlib.sha256(source_id.encode()).hexdigest()
    try:
        module = cst.parse_module(code)
    except cst.ParserSyntaxError:
        return seed, {k: ("", [], "dropped: source does not parse") for k in EDIT_COUNTS}
    order = sorted(RULES)
    random.Random(seed).shuffle(order)
    applicable = [r for r in order if _apply(r, module, seed).code != code]
    out = {}
    for k in EDIT_COUNTS:
        chosen, m, applied = set(applicable[:k]), module, []
        for r in CANON:
            if r in chosen:
                new = _apply(r, m, seed)
                if new.code != m.code:
                    m = new
                    applied.append(r)
        try:
            compile(m.code, source_id, "exec")
            out[k] = (m.code, applied, "kept")
        except SyntaxError as e:
            out[k] = ("", applied, f"dropped: edited code does not parse ({e.msg})")
    return seed, out


def script_version():
    """Git commit of this file (+ "-dirty" if edited since) and the libcst version, which decides codegen."""
    f = "modules/humanize.py"
    try:
        h = subprocess.run(["git", "log", "-1", "--format=%H", "--", f], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip() or "uncommitted"
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", f], cwd=ROOT).returncode != 0
    except FileNotFoundError:
        h, dirty = "unknown", False
    return f"{h}{'-dirty' if dirty else ''} libcst=={version('libcst')}"


def humanize(cfg, force=False):
    d = results_dir(cfg)
    out = d / "human_fixed.csv"
    if force:
        out.unlink(missing_ok=True)
    done = done_ids(out)
    s = read_csv(d / "samples.csv")
    # ponytail: label == "llm" means Direct until #6 adds the category column; it would also catch Style-prompted.
    direct = s[s["category"] == "Direct"] if "category" in s else s[s["label"] == "llm"]
    direct = direct[direct["code"].str.strip() != ""]
    ver = script_version()
    new = dropped = short = 0
    for r in direct.itertuples():
        ids = {k: f"{r.sample_id}:hf{k}" for k in EDIT_COUNTS}
        if all(i in done for i in ids.values()):
            continue
        try:
            seed, results = edit(r.code, r.sample_id)
        except Exception as e:  # a rule bug must not stop the stage; the row records it
            seed, results = "", {k: ("", [], f"dropped: rule error {type(e).__name__}: {e}") for k in EDIT_COUNTS}
        rows = []
        for k, (code, applied, status) in results.items():
            dropped += status != "kept"
            short += status == "kept" and len(applied) < k
            rows.append({"sample_id": ids[k], "source_id": r.sample_id, "problem_id": r.problem_id,
                         "label": "llm", "generator": r.generator, "model_id": r.model_id,
                         "category": "Human-fixed", "edit_count": len(applied), "rules": ";".join(applied),
                         "seed": seed, "script_version": ver, "status": status, "code": code})
        append_csv(rows, out)  # one Direct Sample per write, so a crash resumes
        new += len(rows)
    print(f"human-fixed: {new} new rows, {dropped} dropped (see status column), "
          f"{short} kept with fewer rules than their Edit count target")


# ---------- self-check ----------

_PROGRAMS = [(
    '''from typing import List


def calculate_sum(numbers: List[int]) -> int:
    """Return the sum of the numbers."""
    total_sum = 0
    # Iterate over each number
    for number in numbers:
        total_sum += number
    return total_sum


def is_even(value: int) -> bool:
    return value % 2 == 0


def classify(score: int) -> str:
    if score < 0:
        return "negative"
    return "non-negative"


def main() -> None:
    # Read the input values
    count = int(input())
    values = list(map(int, input().split()))
    squares = [num * num for num in values if is_even(num)]
    result = calculate_sum(squares)
    for index in range(count):
        print(f"Item {index}: {values[index]}")
    for idx, item in enumerate(values):
        if idx == 0:
            continue
        print(idx, item)
    for left, right in zip(values, squares):
        print(left + right)
    print(f"Result: {result} is {classify(result - 10)}")


if __name__ == "__main__":
    main()
''', "4\n1 2 3 4\n", True), (
    '''"""Maximum subarray sum."""
import sys


def max_subarray(arr: list) -> int:
    best: int = arr[0]  # best so far
    current = 0
    for x in arr:
        current = max(x, current + x)
        best = max(best, current)
    return best


def read_ints() -> list:
    return list(map(int, sys.stdin.readline().split()))


n = int(sys.stdin.readline())
data = read_ints()
answer = max_subarray(data)
for i in range(1, n, 2):
    answer += data[i] * 0
print(f"{n} {answer}")
''', "5\n-2 1 -3 4 -1\n", True), (
    # Traps: every rule must back off here, so fewer rules may apply.
    '''class Account:
    def __init__(self, total):
        self.total = total

    def add(self, amount):
        self.total += amount
        return self.total


def area(width, height):
    return width * height


def double(value):
    return value * 2


def shout(text):
    return str(text).upper()


def smaller(a, b):
    return min(a, b)


def pick():
    min = 3
    return smaller(min, 2)


def show_pairs(xs, ys):
    for a, b in zip(xs, ys):
        print(a, b)


def main():
    total = 5
    amount_left = 9
    acct = Account(total)
    print(f"{amount_left=}")
    print(f"{acct.add(3) + total=}")
    print(f"{shout(total)=}")
    print(area(width=2, height=3))
    first = double(int(input()))
    print(f"{first + 1=}", first)
    for i in range(3):
        pass
    print(i)
    for k in range(4):
        if k == 1:
            continue
        print(k)
    v = 7
    squares = [v * v for v in [1, 2, 3]]
    print(squares, v)
    scores = {"a": 1, "b": 2}
    for pos, key in enumerate(scores):
        print(pos, key)
    print(pick())


main()
show_pairs([1, 2], [3, 4])
''', "4\n", False)]


def _run(code, stdin):
    import sys
    r = subprocess.run([sys.executable, "-c", code], input=stdin, capture_output=True, text=True, timeout=5)
    return r.returncode, r.stdout


if __name__ == "__main__":
    changed = set()
    for src, stdin, full in _PROGRAMS:
        want = _run(src, stdin)
        assert want[0] == 0, "test program itself fails"
        m = cst.parse_module(src)
        for r in CANON:  # each rule alone: parses and prints the same
            new = _apply(r, m, "check").code
            if new != src:
                changed.add(r)
                compile(new, r, "exec")
                assert _run(new, stdin) == want, f"rule {r} changed the output:\n{new}"
        for n in range(15):  # many seeds, so many rule combinations
            sid = f"check:{n}"
            seed, res = edit(src, sid)
            assert (seed, res) == edit(src, sid), "not repeatable"
            (c2, a2, s2), (c5, a5, s5) = res[2], res[5]
            assert s2 == s5 == "kept" and set(a2) <= set(a5), (a2, a5)
            assert not full or (len(a2) == 2 and len(a5) == 5), (a2, a5)
            for c in (c2, c5):
                assert _run(c, stdin) == want, f"{sid} changed the output:\n{c}"
    assert changed == set(CANON), f"rules that never fired: {set(CANON) - changed}"
    assert _print_args(cst.parse_expression('f"{a}!"')) is None
    assert _print_args(cst.parse_expression('f" {a}"')) is None
    assert _print_args(cst.parse_expression('f"{a}  {b}"')) is None
    print("humanize self-check ok")
