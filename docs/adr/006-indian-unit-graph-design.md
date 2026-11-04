# ADR-006: Indian Unit Graph Design

## Status
Accepted

## Context

Iðunn is an India-aware kitchen OS. Indian households use a mix of:
- **Metric units**: g, kg, ml, l (modern/standard)
- **Traditional Indian units**: paav (~250g), chamcha (~5ml, Indian teaspoon), katori (~150ml cup)
- **Count units**: piece, bunch, packet

Western pantry apps assume tsp/tbsp/cup (US customary) or ml/l (metric). None handle the Indian traditional units that home cooks actually use when measuring ingredients for dal, sabzi, or atta.

The unit conversion system must:
1. Support all units Indian cooks use
2. Provide accurate conversions for recipe scaling
3. Handle ambiguous units (chamcha = tsp in North, but may differ regionally)
4. Be extensible for regional variations

## Decision

We will implement a **directed conversion graph** using a dictionary of `(from_unit, to_unit) → multiplier` pairs.

### Unit Taxonomy

```python
class Unit(str, Enum):
    # Mass
    GRAM = "g"
    KILOGRAM = "kg"
    PAAV = "paav"  # ~250g traditional

    # Volume
    MILLILITER = "ml"
    LITER = "l"
    TEASPOON = "tsp"  # ~5ml
    TABLESPOON = "tbsp"  # ~15ml
    CHAMCHA = "chamcha"  # Indian tsp, ~5ml
    KATORI = "katori"  # ~150ml, ~2/3 cup

    # Count
    PIECE = "piece"
    BUNCH = "bunch"
    PACKET = "packet"
    BOX = "box"
```

### Conversion Graph

```python
UNIT_CONVERSIONS: dict[tuple[Unit, Unit], float] = {
    # Mass
    (Unit.GRAM, Unit.KILOGRAM): 0.001,
    (Unit.KILOGRAM, Unit.GRAM): 1000.0,
    (Unit.PAAV, Unit.GRAM): 250.0,
    (Unit.GRAM, Unit.PAAV): 1.0 / 250.0,
    (Unit.PAAV, Unit.KILOGRAM): 0.25,
    (Unit.KILOGRAM, Unit.PAAV): 4.0,
    # Volume
    (Unit.MILLILITER, Unit.LITER): 0.001,
    (Unit.LITER, Unit.MILLILITER): 1000.0,
    (Unit.TEASPOON, Unit.MILLILITER): 5.0,
    (Unit.MILLILITER, Unit.TEASPOON): 1.0 / 5.0,
    (Unit.TABLESPOON, Unit.MILLILITER): 15.0,
    (Unit.MILLILITER, Unit.TABLESPOON): 1.0 / 15.0,
    (Unit.CHAMCHA, Unit.MILLILITER): 5.0,
    (Unit.MILLILITER, Unit.CHAMCHA): 1.0 / 5.0,
    (Unit.KATORI, Unit.MILLILITER): 150.0,
    (Unit.MILLILITER, Unit.KATORI): 1.0 / 150.0,
    # Cross-volume
    (Unit.TABLESPOON, Unit.TEASPOON): 3.0,
    (Unit.TEASPOON, Unit.TABLESPOON): 1.0 / 3.0,
    (Unit.CHAMCHA, Unit.TEASPOON): 1.0,  # chamcha ≈ tsp
    (Unit.KATORI, Unit.TABLESPOON): 10.0,  # 150ml / 15ml
    # Mass-Volume water equivalence (approximate)
    (Unit.GRAM, Unit.MILLILITER): 1.0,
    (Unit.MILLILITER, Unit.GRAM): 1.0,
    (Unit.KILOGRAM, Unit.LITER): 1.0,
    (Unit.LITER, Unit.KILOGRAM): 1.0,
}
```

## Rationale

### 1. Graph model is simple, explicit, and testable

A dictionary of conversion pairs is:
- **Easy to understand**: Each entry is a single, testable fact
- **Easy to extend**: Add new units by adding new pairs
- **Property-testable**: Hypothesis can verify roundtrip conversions (g → kg → g)

```python
@given(quantity=st.floats(min_value=0.001, max_value=1000.0))
def test_gram_kilogram_roundtrip(self, quantity):
    item = Item(..., unit=Unit.GRAM, quantity=quantity)
    kg = item.convert_quantity(Unit.KILOGRAM)
    item2 = Item(..., unit=Unit.KILOGRAM, quantity=kg)
    grams_back = item2.convert_quantity(Unit.GRAM)
    assert grams_back == pytest.approx(quantity, rel=1e-6)
```

### 2. Handles Indian traditional units as first-class citizens

Western apps force Indian users to convert mentally ("how many grams is a paav?"). We make it native:

```python
# Recipe says "2 paav atta"
item = Item(name="Atta", quantity=2, unit=Unit.PAAV, ...)

# Convert to kg for shopping
kg = item.convert_quantity(Unit.KILOGRAM)  # Returns 0.5 kg
```

### 3. Approximate mass-volume conversions for water-like substances

Many Indian ingredients are measured by volume but stored/tracked by mass (or vice versa):
- **Water, milk, oil**: ~1 g/ml (handled by the graph)
- **Atta (flour), sugar, salt**: ~1.6 g/ml (NOT handled; would need density)

The current implementation handles the common case (water-like substances). Future work could add density factors per ingredient.

### 4. No transitive conversion (yet)

The graph only supports **direct conversions**. We don't compute transitive paths (g → kg → paav).

**Why?** The full graph is small enough to enumerate all pairs. If we add 50+ units, we'd switch to a transitive graph with BFS/DFS pathfinding.

**Current approach**: Manually add both directions for each conversion.

### 5. UnitConversion model for future region tagging

The `UnitConversion` model is designed for future regional disambiguation:

```python
class UnitConversion(BaseModel):
    from_unit: Unit
    to_unit: Unit
    factor: float
    region: Optional[str] = None  # e.g., "north_india", "south_india"
```

Example future use:
```python
# In North India, 1 katori = 150ml
# In South India, 1 katori might differ slightly
UNIT_CONVERSIONS[(Unit.KATORI, Unit.MILLILITER)] = 150.0  # North
UNIT_CONVERSIONS[(Unit.KATORI, Unit.MILLILITER)] = 160.0  # South (hypothetical)
```

## Consequences

### Positive
- **Simple**: Dictionary lookup is O(1)
- **Testable**: Each conversion is a testable unit
- **India-first**: Traditional units are first-class
- **Property-tested**: Hypothesis verifies roundtrip correctness
- **Extensible**: Add units by adding enum values + conversion pairs

### Negative
- **Manual bidirectional entries**: Must remember to add both (g, kg) and (kg, g)
- **No transitive conversion**: Can't convert g → paav via kg automatically
- **No regional disambiguation yet**: `region` field exists but not implemented in lookup

### Neutral
- **Approximate conversions**: Mass-volume conversions assume water density
- **Limited to 12 units**: If we exceed 50 units, should switch to graph pathfinding

## Alternatives Considered

### 1. Pint library
- **Pros**: Comprehensive unit library, handles transitive conversions
- **Cons**: Adds dependency, bloats for simple use case, Western-centric (no paav/chamcha)

### 2. Full graph with BFS pathfinding
- **Pros**: Automatic transitive conversion, DRY (define each edge once)
- **Cons**: Overkill for 12 units, slower (BFS vs dict lookup), more complex

### 3. pint + custom Indian units
- **Pros**: Leverages pint's power
- **Cons**: Complex setup, hard to understand/modify, overkill

## Testing Strategy

From design doc exit criteria:
> "unit conversions verified by property tests (Hypothesis)"

### Unit tests (example-level)
- `test_gram_to_kilogram`: 1000 g = 1 kg
- `test_paav_to_gram`: 1 paav = 250 g
- `test_chamcha_to_ml`: 1 chamcha = 5 ml
- `test_katori_to_tablespoon`: 1 katori = 10 tbsp

### Property tests (Hypothesis)
- `test_gram_kilogram_roundtrip`: g → kg → g should return original
- `test_ml_liter_roundtrip`: ml → l → ml should return original
- `test_all_conversion_paths_exist`: All defined conversions produce correct results

## References
- [Design Doc Section 5.1: Phase 1 — Inventory core](../../C:/Users/aesir/Work/Projects/Full/Mimir/300%20-%20Work/320%20-%20Personal/322%20-%20Idunn/Idunn-design.md#phase-1--inventory-core-15-weeks)
- [Design Doc Section 6: Tech stack — Hypothesis](../../C:/Users/aesir/Work/Projects/Full/Mimir/300%20-%20Work/320%20-%20Personal/322%20-%20Idunn/Idunn-design.md#6-tech-stack)
- [Pint library](https://pint.readthedocs.io/)

## Date
2026-05-07
