"""
ai_service.py - LM Studio OpenAI-compatible client with robust fallbacks.
Supports Qwen running locally in LM Studio at http://127.0.0.1:1234.
"""

import json
import logging
import re
import httpx
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from config import settings
from prompts import (
    RECIPE_INTERPRETATION_SYSTEM_PROMPT,
    build_recipe_interpretation_prompt,
    MENU_RECOMMENDATION_SYSTEM_PROMPT,
    build_menu_recommendations_prompt,
)

logger = logging.getLogger("marginly.ai_service")

class InterpretedIngredientLine(BaseModel):
    raw_text: str = ""
    matched_ingredient_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    waste_percent: float = 0.0
    notes: Optional[str] = None

class RecipeDraftResponse(BaseModel):
    name: str = "Draft Recipe"
    description: Optional[str] = None
    servings_per_batch: float = 1.0
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    ingredients: List[InterpretedIngredientLine] = []
    clarification_questions: List[str] = []
    ai_status: str = "generated"  # "generated" or "fallback"

class MenuRecommendationsResponse(BaseModel):
    executive_summary: str
    star_actions: List[str] = []
    plowhorse_actions: List[str] = []
    puzzle_actions: List[str] = []
    dog_actions: List[str] = []
    top_priority: str
    ai_status: str = "generated"

def clean_llm_json(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned

async def check_lm_studio_health() -> Dict[str, Any]:
    """
    Checks if LM Studio endpoint is reachable and reports loaded models.
    """
    endpoint = f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(endpoint)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                return {
                    "online": True,
                    "available_models": models,
                    "configured_model": settings.LM_STUDIO_MODEL,
                }
    except Exception as e:
        logger.debug(f"LM Studio health check failed: {e}")
    return {
        "online": False,
        "available_models": [],
        "configured_model": settings.LM_STUDIO_MODEL,
    }

async def call_qwen_chat(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Optional[str]:
    """
    Executes standard OpenAI chat completion JSON payload against LM Studio.
    """
    endpoint = f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LM_STUDIO_API_KEY}"
    }

    # Discover actual loaded model from LM Studio if available
    target_model = settings.LM_STUDIO_MODEL
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            m_resp = await client.get(f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/models")
            if m_resp.status_code == 200:
                m_data = m_resp.json().get("data", [])
                if m_data and len(m_data) > 0:
                    target_model = m_data[0].get("id", settings.LM_STUDIO_MODEL)
    except Exception:
        pass

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=settings.LM_STUDIO_TIMEOUT_SECONDS) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning(f"LM Studio returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.info(f"Local AI request to LM Studio offline or timed out: {e}")
    return None

def fallback_recipe_interpretation(source_text: str) -> RecipeDraftResponse:
    lines = [line.strip() for line in source_text.split("\n") if line.strip()]
    recipe_name = lines[0] if lines else "New Unnamed Recipe"
    ingredient_lines = []

    pattern = re.compile(r"^([\d.]+)\s*([a-zA-Z]+)?\s*(.*)$")

    for line in lines[1:] if len(lines) > 1 else lines:
        qty = None
        unit = None
        matched_name = line

        m = pattern.match(line)
        if m:
            val_str, unit_str, rest = m.groups()
            try:
                qty = float(val_str)
                if unit_str and unit_str.lower() in ['g', 'kg', 'ml', 'l', 'pcs', 'each']:
                    unit = unit_str.lower()
                    matched_name = rest.strip() if rest else line
                else:
                    matched_name = f"{unit_str or ''} {rest or ''}".strip() or line
            except ValueError:
                pass

        ingredient_lines.append(InterpretedIngredientLine(
            raw_text=line,
            matched_ingredient_name=matched_name,
            quantity=qty,
            unit=unit,
            waste_percent=0.0,
            notes="Parsed via fallback parser (LM Studio offline)"
        ))

    return RecipeDraftResponse(
        name=recipe_name,
        description="Draft created from informal text (Deterministic fallback mode)",
        servings_per_batch=1.0,
        yield_quantity=1.0,
        yield_unit="portion",
        ingredients=ingredient_lines,
        clarification_questions=[
            "LM Studio local AI was offline; basic lines parsed deterministically.",
            "Please review quantities and units before confirming the recipe."
        ],
        ai_status="fallback"
    )

async def interpret_recipe_text(source_text: str, catalog_ingredient_names: List[str]) -> RecipeDraftResponse:
    user_prompt = build_recipe_interpretation_prompt(source_text, catalog_ingredient_names)
    ai_raw = await call_qwen_chat(
        system_prompt=RECIPE_INTERPRETATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.1
    )

    if ai_raw:
        try:
            cleaned = clean_llm_json(ai_raw)
            data = json.loads(cleaned)
            draft = RecipeDraftResponse(**data)
            draft.ai_status = "generated"
            return draft
        except Exception as err:
            logger.warning(f"Failed to parse Qwen JSON response: {err}. Using fallback.")

    return fallback_recipe_interpretation(source_text)

def fallback_menu_recommendations(summary_dict: dict) -> MenuRecommendationsResponse:
    stars = summary_dict.get("stars_count", 0)
    plowhorses = summary_dict.get("plowhorses_count", 0)
    puzzles = summary_dict.get("puzzles_count", 0)
    dogs = summary_dict.get("dogs_count", 0)

    star_actions = [
        "Protect quality and consistency rigorously; these are your signature cash generators.",
        "Maintain current portion sizes and do not compromise on ingredient grades."
    ] if stars > 0 else ["No Star items identified yet. Focus on creating a high-margin, popular signature dish."]

    plowhorse_actions = [
        "Test a small incremental price increase (5-8%) to capture more contribution margin without hurting volume.",
        "Audit ingredient waste and negotiate bulk pricing with suppliers for high-volume inputs."
    ] if plowhorses > 0 else ["No Plowhorses currently on the menu."]

    puzzle_actions = [
        "Feature prominently as chef's specials, weekly highlights, or table-top tent cards.",
        "Train front-of-house service staff to actively suggest and describe these dishes."
    ] if puzzles > 0 else ["No Puzzles currently on the menu."]

    dog_actions = [
        "Audit recipes to see if costly perishable ingredients can be shared across other dishes.",
        "Consider replacing with a fresh seasonal item or removing from active menu."
    ] if dogs > 0 else ["No Dog items in this period. Great menu curation!"]

    top_priority = (
        "Re-engineer Plowhorses to improve gross margins by 5% and promote Puzzles through server recommendations."
        if plowhorses > 0 else "Focus on maintaining consistent quality for Star items and testing new high-margin specials."
    )

    return MenuRecommendationsResponse(
        executive_summary=(
            f"Menu breakdown: {stars} Star(s), {plowhorses} Plowhorse(s), "
            f"{puzzles} Puzzle(s), and {dogs} Dog(s). Average contribution margin is "
            f"₹{summary_dict.get('average_contribution_margin', 0):.2f}."
        ),
        star_actions=star_actions,
        plowhorse_actions=plowhorse_actions,
        puzzle_actions=puzzle_actions,
        dog_actions=dog_actions,
        top_priority=top_priority,
        ai_status="fallback"
    )

async def generate_menu_recommendations(summary_dict: dict, currency_symbol: str = "₹") -> MenuRecommendationsResponse:
    user_prompt = build_menu_recommendations_prompt(summary_dict, currency_symbol)
    ai_raw = await call_qwen_chat(
        system_prompt=MENU_RECOMMENDATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3
    )

    if ai_raw:
        try:
            cleaned = clean_llm_json(ai_raw)
            data = json.loads(cleaned)
            recs = MenuRecommendationsResponse(**data)
            recs.ai_status = "generated"
            return recs
        except Exception as e:
            logger.warning(f"Error parsing recommendations from Qwen: {e}. Using fallback.")

    return fallback_menu_recommendations(summary_dict)
