---
name: tdd
description: Test-driven development with red-green-refactor. Build features or fix bugs one vertical slice at a time.
argument-hint: "[feature or bug description]"
allowed-tools:
  - read_file
  - write_to_file
  - edit
  - multi_edit
  - grep_search
  - find_by_name
  - bash
  - command_status
  - todo_list
  - skill
  - list_resources
  - read_resource
  - search_web
  - read_url_content
triggers:
  - user
  - model
subagent: false
priority: high
auto-apply:
  - "tdd"
  - "测试驱动开发"
  - "red green refactor"
  - "red-green-refactor"
  - "先写测试"
  - "先写测试再实现"
  - "用 TDD 修 bug"
  - "用 TDD 写功能"
file-patterns:
  - "tests/**/*.py"
  - "test_*.py"
  - "**/test_*.py"
  - "**/conftest.py"
excluded-patterns:
  - "**/venv/**"
  - "**/__pycache__/**"
  - "**/.git/**"
  - "**/node_modules/**"
keywords:
  - "tdd"
  - "test-driven"
  - "red-green-refactor"
  - "seam"
  - "vertical slice"
  - "mock"
  - "pytest"
---

# Test-Driven Development

TDD is the **red → green** loop. Work one vertical slice at a time: one confirmed seam, one failing test, one minimal implementation, then move to the next behavior. Consult this skill before and during every cycle, not after.

## What a good test is

Tests verify **behavior through public interfaces**, not implementation details. A good test reads like a specification, survives refactors, and has one logical assertion.

```python
# GOOD: tests observable behavior
@pytest.mark.asyncio
async def test_user_can_checkout_with_valid_cart():
    cart = create_cart()
    cart.add(product)
    result = await checkout(cart, payment_method)
    assert result.status == "confirmed"
```

A good test:
- Tests behavior users/callers care about.
- Uses the public API only.
- Survives internal refactors.
- Describes **what**, not **how**.
- Has one logical assertion per test.

## Seams — where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user.

Ask: "What's the public interface, and which seams should we test?"

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods, asserts call counts, or verifies through side channels like querying the database directly. The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological** — the expected value is recomputed the same way the code computes it, so the test passes by construction. Expected values must come from an independent source of truth: a known-good literal, a worked example, or the spec.
- **Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify *imagined* behavior and commit to test structure before you understand the implementation. Work in **vertical slices** instead: one test → one implementation → repeat.

## Rules of the loop

1. **Red before green.** Write exactly one failing test for the next behavior. Then write only enough code to make that test pass. Do not anticipate future tests or add speculative features.
2. **One slice at a time.** One seam, one test, one minimal implementation per cycle.
3. **Refactoring is not part of the loop.** It belongs to the review stage (use the `testing-debugging` or `code-review` discipline), not the red → green implementation cycle.

## Running the loop in this project

1. Identify the next seam and behavior with the user.
2. Write the failing test in the appropriate `tests/` directory.
3. Run the test to confirm it fails:
   ```powershell
   python -m pytest tests/path/test_file.py -k test_name -v
   ```
   Or use the project scripts from `AGENTS.md`:
   ```powershell
   python scripts/run_core_api_infrastructure_tests.py
   ```
4. Implement the minimum code to pass the test.
5. Run the test again to confirm it passes.
6. Move to the next seam/behavior.

## Good and bad test examples

### Mocking internal collaborators is bad
```python
# BAD: coupled to internal payment service call
@pytest.mark.asyncio
async def test_checkout_calls_payment_service():
    with patch("app.services.payment.process") as mock_process:
        await checkout(cart, payment)
        mock_process.assert_called_once_with(cart.total)
```

### Bypassing the interface is bad
```python
# BAD: verifies through the database instead of the public API
@pytest.mark.asyncio
async def test_create_user_saves_to_database():
    await create_user(name="Alice")
    row = await db.fetch_one("SELECT * FROM users WHERE name = ?", ["Alice"])
    assert row is not None

# GOOD: verifies through the interface
@pytest.mark.asyncio
async def test_create_user_makes_user_retrievable():
    user = await create_user(name="Alice")
    retrieved = await get_user(user.id)
    assert retrieved.name == "Alice"
```

### Tautological tests are bad
```python
# BAD: expected value is recomputed the same way the code does
def test_calculate_total_sums_line_items():
    items = [{"price": 10}, {"price": 5}]
    expected = sum(item["price"] for item in items)
    assert calculate_total(items) == expected

# GOOD: expected value is an independent literal
def test_calculate_total_sums_line_items():
    assert calculate_total([{"price": 10}, {"price": 5}]) == 15
```

## When to mock

Mock at **system boundaries** only:
- External APIs (payment, email, etc.)
- Databases (prefer a test database when possible)
- Time, randomness, UUIDs
- File system (sometimes)

**Do not mock:**
- Your own classes or modules
- Internal collaborators
- Anything you control

## Designing for mockability

Use **dependency injection** for external dependencies:

```python
# Easy to mock
async def process_payment(order, payment_client):
    return await payment_client.charge(order.total)

# Hard to mock
async def process_payment(order):
    client = StripeClient(os.environ["STRIPE_KEY"])
    return await client.charge(order.total)
```

Prefer **SDK-style interfaces** over generic fetchers:

```python
# GOOD: each function is independently mockable
async def get_user(user_id: int) -> User: ...
async def get_orders(user_id: int) -> list[Order]: ...
async def create_order(data: OrderCreate) -> Order: ...

# BAD: one generic function requires conditional logic inside the mock
async def fetch(endpoint: str, **kwargs): ...
```

## Before starting

Read `CONTEXT.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you are touching.
