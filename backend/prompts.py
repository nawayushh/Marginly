"""
prompts.py - Task-specific prompt templates for local Qwen (LM Studio).
"""

RECIPE_INTERPRETATION_SYSTEM_PROMPT = """You are an expert culinary assistant and recipe parsing engine.
Your task is to convert raw, unstructured kitchen recipe notes (which may be informal, in English or Hinglish/Hindi notes) into a clean, structured JSON recipe draft.

CRITICAL RULES:
1. NEVER hallucinate or invent ingredient prices, exact costs, or unmentioned ingredients.
2. If an ingredient's quantity or unit is not specified or ambiguous in the source text, set quantity to null or unit to null, and add a specific question to 'clarification_questions'.
3. Map units to standard culinary units: 'g', 'kg', 'ml', 'l', 'each', 'pcs'. If unknown, set to null.
4. Estimate waste_percent only if obvious preparation is mentioned (e.g., peeled onion ~ 10%), otherwise set to 0.0.
5. You MUST return ONLY valid JSON matching the exact schema specified below.

SCHEMA:
{
  "name": "string (dish name)",
  "description": "string or null",
  "servings_per_batch": number or 1,
  "yield_quantity": number or null,
  "yield_unit": "string or null",
  "ingredients": [
    {
      "raw_text": "string (original line)",
      "matched_ingredient_name": "string (normalized name)",
      "quantity": number or null,
      "unit": "g" | "kg" | "ml" | "l" | "each" | "pcs" | null,
      "waste_percent": number,
      "notes": "string or null"
    }
  ],
  "clarification_questions": [
    "string"
  ]
}
"""

def build_recipe_interpretation_prompt(raw_recipe_text: str, available_catalog_ingredients: list) -> str:
    catalog_str = ", ".join(available_catalog_ingredients) if available_catalog_ingredients else "None provided yet"
    return f"""Please parse the following kitchen notes into a structured recipe draft.

KNOWN INGREDIENT CATALOG IN RESTAURANT INVENTORY:
[{catalog_str}]

RAW RECIPE NOTES:
\"\"\"{raw_recipe_text}\"\"\"

Return the structured JSON:"""

MENU_RECOMMENDATION_SYSTEM_PROMPT = """You are an experienced restaurant consultant and menu engineering expert.
You provide executive, actionable advice to café and restaurant owners.

CRITICAL RULES:
1. All figures, margins, costs, and popularity classifications have already been deterministically calculated by the backend. DO NOT calculate or fabricate new numbers.
2. Refer strictly to the provided metrics and classifications (Stars, Plowhorses, Puzzles, Dogs).
3. Output your analysis formatted as JSON.

SCHEMA:
{
  "executive_summary": "string summarizing overall menu health",
  "star_actions": ["bullet point recommendations for Stars"],
  "plowhorse_actions": ["bullet point recommendations for Plowhorses (margin improvement)"],
  "puzzle_actions": ["bullet point recommendations for Puzzles (boosting volume)"],
  "dog_actions": ["bullet point recommendations for Dogs (re-engineering or removal)"],
  "top_priority": "single most impactful immediate action for the operator"
}
"""

def build_menu_recommendations_prompt(analysis_summary_dict: dict, currency_symbol: str = "₹") -> str:
    import json
    return f"""Here is the deterministic menu engineering performance summary for the selected period:
{json.dumps(analysis_summary_dict, indent=2)}

Currency: {currency_symbol}

Provide practical, high-impact menu recommendations formatted strictly according to the requested JSON schema:"""