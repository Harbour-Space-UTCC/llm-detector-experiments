"""Edit rules must keep each program's output, repeat exactly, and nest Edit count 2 inside 5.

Run: python -m pytest tests/
"""
import subprocess
import sys

import libcst as cst
import pytest

from modules.humanize import CANON, _apply, _print_args, edit

# (source, stdin, full). full=True: every rule has something to edit, so each Edit count is met exactly.
# full=False is a trap program where every rule must back off, so fewer rules may apply.
PROGRAMS = [(
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


def run(code, stdin):
    r = subprocess.run([sys.executable, "-c", code], input=stdin, capture_output=True, text=True, timeout=5)
    return r.returncode, r.stdout


@pytest.fixture(scope="module", params=range(len(PROGRAMS)), ids=["ai_style", "script_style", "traps"])
def program(request):
    src, stdin, full = PROGRAMS[request.param]
    want = run(src, stdin)
    assert want[0] == 0, "test program itself fails"
    return src, stdin, full, want


@pytest.mark.parametrize("rule", CANON)
def test_rule_alone_keeps_output(program, rule):
    src, stdin, _, want = program
    new = _apply(rule, cst.parse_module(src), "check").code
    compile(new, rule, "exec")
    assert run(new, stdin) == want, f"rule {rule} changed the output:\n{new}"


@pytest.mark.parametrize("n", range(15))  # many seeds, so many rule combinations
def test_edit_counts(program, n):
    src, stdin, full, want = program
    sid = f"check:{n}"
    seed, res = edit(src, sid)
    assert (seed, res) == edit(src, sid), "not repeatable"
    (c2, a2, s2), (c5, a5, s5) = res[2], res[5]
    assert s2 == s5 == "kept"
    assert set(a2) <= set(a5), "Edit count 5 must include the Edit count 2 rules"
    if full:
        assert (len(a2), len(a5)) == (2, 5)
    for c in (c2, c5):
        assert run(c, stdin) == want, f"{sid} changed the output:\n{c}"


def test_every_rule_fires():
    changed = {r for src, _, _ in PROGRAMS for r in CANON
               if _apply(r, cst.parse_module(src), "check").code != src}
    assert changed == set(CANON)


def test_source_that_does_not_parse_is_dropped():
    _, res = edit("def (:", "bad")
    assert all(status == "dropped: source does not parse" for _, _, status in res.values())


@pytest.mark.parametrize("fstring", ['f"{a}!"', 'f" {a}"', 'f"{a}  {b}"', 'f"{a!r} {b}"', 'f"{a=}"'])
def test_fstring_left_alone_when_print_would_differ(fstring):
    assert _print_args(cst.parse_expression(fstring)) is None


def test_fstring_split_into_print_args():
    items = _print_args(cst.parse_expression('f"Sum: {a} and {b}"'))
    assert [cst.Module([]).code_for_node(i) for i in items] == ['"Sum:"', "a", '"and"', "b"]
