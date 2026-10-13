"""
menu_analysis.py - Deterministic business calculations for Marginly.

STRICT AI BOUNDARY:
All unit conversions, costing, waste adjustments, margins, popularity,
and menu classifications MUST occur here via deterministic Python arithmetic.
LLMs are never queried for mathematical calculations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

# -------------------------------------------------------------------------
# Supported Units & Base Unit Mappings
# -------------------------------------------------------------------------
MASS_CONVERSIONS = {
    "kg": Decimal("1000"),
    "g": Decimal("1"),
    "mg": Decimal("0.001"),
}

VOLUME_CONVERSIONS = {
    "l": Decimal("1000"),
    "ml": Decimal("1"),
}

COUNT_CONVERSIONS = {
    "each": Decimal("1"),
    "pcs": Decimal("1"),
    "piece": Decimal("1"),
    "unit": Decimal("1"),
}

def normalize_unit_str(unit: str) -> str:
    return unit.strip().lower()

def convert_unit(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """
    Convert a quantity between supported metric and count units.
    Mass: kg, g, mg -> base unit g
    Volume: l, ml -> base unit ml
    Count: each, pcs -> base unit each
    Volume-to-mass conversions are strictly prohibited without density.
    """
    u_from = normalize_unit_str(from_unit)
    u_to = normalize_unit_str(to_unit)

    if u_from == u_to:
        return quantity

    if u_from in MASS_CONVERSIONS and u_to in MASS_CONVERSIONS:
        base_val = quantity * MASS_CONVERSIONS[u_from]
        return base_val / MASS_CONVERSIONS[u_to]

    if u_from in VOLUME_CONVERSIONS and u_to in VOLUME_CONVERSIONS:
        base_val = quantity * VOLUME_CONVERSIONS[u_from]
        return base_val / VOLUME_CONVERSIONS[u_to]

    if u_from in COUNT_CONVERSIONS and u_to in COUNT_CONVERSIONS:
        base_val = quantity * COUNT_CONVERSIONS[u_from]
        return base_val / COUNT_CONVERSIONS[u_to]

    raise ValueError(
        f"Unsupported unit conversion from '{from_unit}' to '{to_unit}'. "
        f"Cannot convert between different physical dimensions (e.g., volume to mass) without density."
    )

# -------------------------------------------------------------------------
# Costing & Waste Calculation
# -------------------------------------------------------------------------
def calculate_ingredient_line_cost(
    quantity: Decimal,
    unit: str,
    base_unit: str,
    current_unit_price: Decimal,
    waste_percent: Decimal = Decimal("0"),
) -> Tuple[Decimal, Decimal]:
    """
    Calculates line cost.
    Documented waste rule:
    'waste_percent' represents the percentage of purchased ingredient lost during prep.
    Therefore, to get 'usable_quantity', the operator must purchase:
    effective_purchased_quantity = usable_quantity / (1 - waste_percent / 100)
    
    Returns:
        (effective_base_quantity, line_cost)
    """
    if waste_percent < Decimal("0") or waste_percent >= Decimal("100"):
        raise ValueError(f"Waste percent must be between 0 and 99.99%. Got: {waste_percent}")

    # Convert entered quantity to ingredient's base unit
    qty_in_base = convert_unit(quantity, unit, base_unit)

    # Apply waste factor
    if waste_percent > Decimal("0"):
        effective_base_qty = qty_in_base / (Decimal("1") - (waste_percent / Decimal("100")))
    else:
        effective_base_qty = qty_in_base

    line_cost = effective_base_qty * current_unit_price
    return (effective_base_qty, line_cost)

def calculate_recipe_cost(
    line_costs: List[Decimal],
    servings_per_batch: Decimal,
    batch_overhead_cost: Decimal = Decimal("0")
) -> Tuple[Decimal, Decimal]:
    """
    Computes batch cost and cost per serving.
    """
    if servings_per_batch <= Decimal("0"):
        raise ValueError("servings_per_batch must be greater than zero.")

    total_batch_cost = sum(line_costs) + batch_overhead_cost
    cost_per_serving = total_batch_cost / servings_per_batch
    return (total_batch_cost, cost_per_serving)

# -------------------------------------------------------------------------
# Margins and Menu Engineering Metrics
# -------------------------------------------------------------------------
class MenuItemMetrics(BaseModel):
    item_id: int
    name: str
    category: str
    selling_price: float
    cost_per_serving: float
    quantity_sold: int
    revenue: float
    contribution_margin_per_item: float
    total_contribution: float
    margin_percentage: float
    popularity_percentage: float
    classification: str = "Insufficient Data"
    explanation: str = ""

class MenuAnalysisSummary(BaseModel):
    total_items: int
    total_quantity_sold: int
    total_revenue: float
    total_contribution: float
    average_contribution_margin: float
    popularity_threshold_percent: float
    stars_count: int
    plowhorses_count: int
    puzzles_count: int
    dogs_count: int
    items: List[MenuItemMetrics]

def compute_menu_engineering_matrix(
    items_data: List[Dict[str, Any]],
    popularity_factor: float = 1.0,
    comparison_scope_name: str = "Full Menu"
) -> MenuAnalysisSummary:
    """
    Implements standard Kasavana & Smith menu engineering matrix:
    - Popularity benchmark: (100% / N) * popularity_factor
    - Profitability benchmark: Weighted average Contribution Margin per item
    
    Classifications:
    - Star: Popularity >= threshold AND CM >= threshold
    - Plowhorse: Popularity >= threshold AND CM < threshold
    - Puzzle: Popularity < threshold AND CM >= threshold
    - Dog: Popularity < threshold AND CM < threshold
    """
    n_items = len(items_data)
    if n_items == 0:
        return MenuAnalysisSummary(
            total_items=0,
            total_quantity_sold=0,
            total_revenue=0.0,
            total_contribution=0.0,
            average_contribution_margin=0.0,
            popularity_threshold_percent=0.0,
            stars_count=0,
            plowhorses_count=0,
            puzzles_count=0,
            dogs_count=0,
            items=[]
        )

    total_qty_sold = sum(int(item.get("quantity_sold", 0)) for item in items_data)
    total_revenue_dec = Decimal("0")
    total_contrib_dec = Decimal("0")
    processed_items = []

    for item in items_data:
        selling_price = Decimal(str(item.get("selling_price", 0)))
        cost_per_serving = Decimal(str(item.get("cost_per_serving", 0)))
        qty = Decimal(str(item.get("quantity_sold", 0)))

        rev = selling_price * qty
        cm_per_item = selling_price - cost_per_serving
        tot_cm = cm_per_item * qty

        total_revenue_dec += rev
        total_contrib_dec += tot_cm

        margin_pct = (cm_per_item / selling_price * Decimal("100")) if selling_price > Decimal("0") else Decimal("0")
        pop_pct = (qty / Decimal(str(total_qty_sold)) * Decimal("100")) if total_qty_sold > 0 else Decimal("0")

        processed_items.append({
            "item_id": item.get("id", 0),
            "name": item.get("name", "Unknown"),
            "category": item.get("category", "General"),
            "selling_price": float(selling_price),
            "cost_per_serving": float(cost_per_serving),
            "quantity_sold": int(qty),
            "revenue": float(rev),
            "cm_per_item": cm_per_item,
            "tot_cm": tot_cm,
            "margin_percentage": float(margin_pct),
            "popularity_percentage": float(pop_pct),
        })

    pop_threshold = (Decimal("100") / Decimal(str(n_items))) * Decimal(str(popularity_factor))

    if total_qty_sold > 0:
        avg_cm = total_contrib_dec / Decimal(str(total_qty_sold))
    else:
        avg_cm = sum(item["cm_per_item"] for item in processed_items) / Decimal(str(n_items))

    stars, plowhorses, puzzles, dogs = 0, 0, 0, 0
    final_items: List[MenuItemMetrics] = []

    for p in processed_items:
        cm = p["cm_per_item"]
        pop = Decimal(str(p["popularity_percentage"]))

        if total_qty_sold == 0:
            classification = "Insufficient Data"
            explanation = "No sales recorded in this period to evaluate popularity."
        else:
            is_high_pop = pop >= pop_threshold
            is_high_profit = cm >= avg_cm

            if is_high_pop and is_high_profit:
                classification = "Star"
                stars += 1
                explanation = "High profitability and high sales volume. Keep quality and presentation consistent."
            elif is_high_pop and not is_high_profit:
                classification = "Plowhorse"
                plowhorses += 1
                explanation = "Popular dish with below-average margin. Consider modest price increase or portion optimization."
            elif not is_high_pop and is_high_profit:
                classification = "Puzzle"
                puzzles += 1
                explanation = "Highly profitable but lower sales volume. Promote via specials, menu placement, or server recommendations."
            else:
                classification = "Dog"
                dogs += 1
                explanation = "Low margin and low sales volume. Candidate for recipe re-engineering, price hike, or menu removal."

        final_items.append(MenuItemMetrics(
            item_id=p["item_id"],
            name=p["name"],
            category=p["category"],
            selling_price=p["selling_price"],
            cost_per_serving=p["cost_per_serving"],
            quantity_sold=p["quantity_sold"],
            revenue=p["revenue"],
            contribution_margin_per_item=float(round(p["cm_per_item"], 2)),
            total_contribution=float(round(p["tot_cm"], 2)),
            margin_percentage=float(round(Decimal(str(p["margin_percentage"])), 2)),
            popularity_percentage=float(round(Decimal(str(p["popularity_percentage"])), 2)),
            classification=classification,
            explanation=explanation,
        ))

    return MenuAnalysisSummary(
        total_items=n_items,
        total_quantity_sold=total_qty_sold,
        total_revenue=float(round(total_revenue_dec, 2)),
        total_contribution=float(round(total_contrib_dec, 2)),
        average_contribution_margin=float(round(avg_cm, 2)),
        popularity_threshold_percent=float(round(pop_threshold, 2)),
        stars_count=stars,
        plowhorses_count=plowhorses,
        puzzles_count=puzzles,
        dogs_count=dogs,
        items=final_items
    )
