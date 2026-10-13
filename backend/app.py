"""
app.py - FastAPI application for Marginly.

Features:
- SQLite persistence (standard Python sqlite3) for ingredients, price history, recipes,
  recipe lines, menu items, and sales records.
- Deterministic calculation endpoints.
- Task-specific Qwen integration via LM Studio with automatic fallback.
- Price alert detection on ingredient price changes.
- CORS configured for Vite frontend (http://localhost:5173).
- Seed demo dataset on startup if database is empty.
"""

import os
import sqlite3
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import uuid
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from menu_analysis import (
    convert_unit,
    calculate_ingredient_line_cost,
    calculate_recipe_cost,
    compute_menu_engineering_matrix,
    MenuAnalysisSummary,
)
from ai_service import (
    check_lm_studio_health,
    interpret_recipe_text,
    generate_menu_recommendations,
    RecipeDraftResponse,
    MenuRecommendationsResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marginly.api")

# -------------------------------------------------------------------------
# SQLite Database Helpers
# -------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Profile / Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY,
        restaurant_name TEXT NOT NULL,
        currency TEXT NOT NULL,
        currency_symbol TEXT NOT NULL
    );
    """)

    # 2. Ingredients
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        base_unit TEXT NOT NULL, -- 'g', 'ml', 'each'
        current_unit_price REAL NOT NULL, -- price per single base unit
        currency TEXT NOT NULL DEFAULT 'INR',
        supplier TEXT,
        last_price_updated_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 3. Price History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredient_price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient_id INTEGER NOT NULL,
        old_price REAL NOT NULL,
        new_price REAL NOT NULL,
        change_percentage REAL NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
    );
    """)

    # 4. Recipes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        source_text TEXT,
        servings_per_batch REAL NOT NULL DEFAULT 1.0,
        yield_quantity REAL,
        yield_unit TEXT,
        batch_overhead_cost REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'confirmed', -- 'draft', 'confirmed'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 5. Recipe Ingredient Lines
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_id INTEGER,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        waste_percent REAL NOT NULL DEFAULT 0.0,
        notes TEXT,
        FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE SET NULL
    );
    """)

    # 6. Menu Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Main Course',
        recipe_id INTEGER,
        selling_price REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'INR',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE SET NULL
    );
    """)

    # 7. Sales Records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_item_id INTEGER NOT NULL,
        period TEXT NOT NULL, -- e.g., '2026-Q1', 'October 2026'
        quantity_sold INTEGER NOT NULL,
        channel TEXT DEFAULT 'Dine-in',
        created_at TEXT NOT NULL,
        UNIQUE(menu_item_id, period, channel),
        FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE
    );
    """)

    # 8. Alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT NOT NULL, -- 'PRICE_SPIKE', 'NEGATIVE_MARGIN', 'COST_CHANGE'
        severity TEXT NOT NULL, -- 'warning', 'critical', 'info'
        message TEXT NOT NULL,
        item_id INTEGER,
        created_at TEXT NOT NULL
    );
    """)

    # 9. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        restaurant_name TEXT,
        location TEXT,
        cuisine_type TEXT,
        role TEXT NOT NULL DEFAULT 'owner',
        created_at TEXT NOT NULL
    );
    """)

    # 10. Auth Tokens
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Initialize default profile if empty
    cursor.execute("SELECT COUNT(*) as count FROM profile;")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO profile (id, restaurant_name, currency, currency_symbol)
        VALUES (1, ?, ?, ?);
        """, (settings.RESTAURANT_NAME, settings.DEFAULT_CURRENCY, settings.DEFAULT_CURRENCY_SYMBOL))

    conn.commit()
    conn.close()

def seed_default_user():
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    import hashlib
    cursor.execute("SELECT COUNT(*) as count FROM users;")
    if cursor.fetchone()["count"] == 0:
        pw_hash = hashlib.sha256("abc123".encode()).hexdigest()
        cursor.execute("""
        INSERT INTO users (username, password_hash, display_name, restaurant_name, location, cuisine_type, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("abc123", pw_hash, "Restaurant Owner", "My Restaurant", "Auto-detected", "Multi-Cuisine", "owner", now))
        conn.commit()
    conn.close()

def seed_demo_data_if_empty():
    seed_default_user()
    # Don't auto-seed demo dishes/ingredients by default to keep blank for user calculations
    return

    now = datetime.now(timezone.utc).isoformat()

    # Seed Ingredients (Stored with price per base unit: g, ml, each)
    # E.g. Espresso Beans: ₹1200/kg -> ₹1.20 per gram
    # Whole Milk: ₹65/L -> ₹0.065 per ml
    # Chicken Breast: ₹320/kg -> ₹0.32 per gram
    # Basmati Rice: ₹110/kg -> ₹0.11 per gram
    # Butter: ₹540/kg -> ₹0.54 per gram
    # Paneer: ₹420/kg -> ₹0.42 per gram
    # Cooking Oil: ₹160/L -> ₹0.16 per ml
    # Flour / Maida: ₹45/kg -> ₹0.045 per gram
    # Onions: ₹35/kg -> ₹0.035 per gram
    # Tomatoes: ₹40/kg -> ₹0.040 per gram
    # Burger Bun: ₹15 each -> ₹15.0 per each
    # Cheese Slice: ₹12 each -> ₹12.0 per each

    ingredients_seed = [
        ("Espresso Coffee Beans", "g", 1.20, "Roaster's Hub", now),
        ("Whole Milk", "ml", 0.065, "Local Dairy Farm", now),
        ("Fresh Paneer", "g", 0.42, "Dairy Co", now),
        ("Basmati Rice", "g", 0.11, "Grain Wholesaler", now),
        ("Chicken Breast", "g", 0.32, "City Meat Supplier", now),
        ("Table Butter", "g", 0.54, "Dairy Co", now),
        ("Refined Sunflower Oil", "ml", 0.16, "Grocery Mart", now),
        ("Yellow Onions", "g", 0.035, "Veggie Mandi", now),
        ("Fresh Tomatoes", "g", 0.040, "Veggie Mandi", now),
        ("Brioche Burger Bun", "each", 15.0, "Artisan Bakery", now),
        ("Cheddar Cheese Slice", "each", 12.0, "Dairy Co", now),
    ]

    for name, unit, price, supplier, dt in ingredients_seed:
        cursor.execute("""
        INSERT INTO ingredients (name, base_unit, current_unit_price, supplier, last_price_updated_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (name, unit, price, supplier, dt, dt))

    # Seed Recipes
    # Recipe 1: Café Latte (1 serving)
    cursor.execute("""
    INSERT INTO recipes (name, description, source_text, servings_per_batch, batch_overhead_cost, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "Café Latte",
        "Classic espresso drink with steamed velvety milk",
        "18g espresso beans, 220ml steamed whole milk",
        1.0,
        2.0, # ₹2 overhead for cup and stirrer
        "confirmed",
        now, now
    ))
    latte_id = cursor.lastrowid
    # Lines for Latte
    cursor.execute("SELECT id FROM ingredients WHERE name='Espresso Coffee Beans';")
    bean_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Whole Milk';")
    milk_id = cursor.fetchone()["id"]
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 18, 'g', 2.0);", (latte_id, bean_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 220, 'ml', 5.0);", (latte_id, milk_id))

    # Recipe 2: Paneer Butter Masala (Batch for 4 servings)
    cursor.execute("""
    INSERT INTO recipes (name, description, source_text, servings_per_batch, batch_overhead_cost, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "Paneer Butter Masala",
        "Rich tomato and butter gravy with cottage cheese cubes",
        "400g Paneer, 100g Butter, 400g Tomatoes, 200g Onions, 30ml Oil",
        4.0,
        15.0, # gas & spice blend
        "confirmed",
        now, now
    ))
    pbm_id = cursor.lastrowid
    cursor.execute("SELECT id FROM ingredients WHERE name='Fresh Paneer';")
    paneer_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Table Butter';")
    butter_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Fresh Tomatoes';")
    tomato_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Yellow Onions';")
    onion_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Refined Sunflower Oil';")
    oil_id = cursor.fetchone()["id"]

    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 400, 'g', 0.0);", (pbm_id, paneer_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 100, 'g', 0.0);", (pbm_id, butter_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 400, 'g', 8.0);", (pbm_id, tomato_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 200, 'g', 12.0);", (pbm_id, onion_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 30, 'ml', 0.0);", (pbm_id, oil_id))

    # Recipe 3: Classic Crispy Chicken Burger (1 serving)
    cursor.execute("""
    INSERT INTO recipes (name, description, source_text, servings_per_batch, batch_overhead_cost, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "Crispy Chicken Burger",
        "Seasoned chicken breast with brioche bun and cheddar",
        "1 bun, 150g chicken breast, 1 cheddar slice, 20ml oil",
        1.0,
        5.0, # packaging and fry overhead
        "confirmed",
        now, now
    ))
    burger_id = cursor.lastrowid
    cursor.execute("SELECT id FROM ingredients WHERE name='Brioche Burger Bun';")
    bun_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Chicken Breast';")
    chicken_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM ingredients WHERE name='Cheddar Cheese Slice';")
    cheese_id = cursor.fetchone()["id"]

    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 1, 'each', 0.0);", (burger_id, bun_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 150, 'g', 5.0);", (burger_id, chicken_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 1, 'each', 0.0);", (burger_id, cheese_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 20, 'ml', 0.0);", (burger_id, oil_id))

    # Recipe 4: Steamed Basmati Rice (Batch for 5 servings)
    cursor.execute("""
    INSERT INTO recipes (name, description, source_text, servings_per_batch, batch_overhead_cost, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "Steamed Basmati Rice",
        "Fragrant steamed long-grain basmati rice",
        "500g Basmati Rice, 5g Butter",
        5.0,
        5.0,
        "confirmed",
        now, now
    ))
    rice_rec_id = cursor.lastrowid
    cursor.execute("SELECT id FROM ingredients WHERE name='Basmati Rice';")
    rice_ing_id = cursor.fetchone()["id"]
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 500, 'g', 0.0);", (rice_rec_id, rice_ing_id))
    cursor.execute("INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent) VALUES (?, ?, 10, 'g', 0.0);", (rice_rec_id, butter_id))

    # Seed Menu Items & Sales for period "Current Month"
    # Latte: price 190, sold 320 (Star: high CM ₹150+, high popularity)
    # Burger: price 280, sold 210 (Star/Plowhorse depending on mix)
    # Paneer Butter Masala: price 320, sold 110 (Puzzle: High CM, moderate popularity)
    # Steamed Basmati Rice: price 120, sold 85 (Dog: Low CM, low popularity)
    menu_items_seed = [
        ("Café Latte", "Beverages", latte_id, 190.0, 340),
        ("Crispy Chicken Burger", "Burgers & Sandwiches", burger_id, 260.0, 260),
        ("Paneer Butter Masala", "Curries", pbm_id, 320.0, 110),
        ("Steamed Basmati Rice", "Sides", rice_rec_id, 90.0, 75),
    ]

    for m_name, cat, r_id, price, qty_sold in menu_items_seed:
        cursor.execute("""
        INSERT INTO menu_items (name, category, recipe_id, selling_price, created_at)
        VALUES (?, ?, ?, ?, ?);
        """, (m_name, cat, r_id, price, now))
        item_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO sales_records (menu_item_id, period, quantity_sold, channel, created_at)
        VALUES (?, 'Current Month', ?, 'Dine-in', ?);
        """, (item_id, qty_sold, now))

    # Seed default user
    import hashlib
    cursor.execute("SELECT COUNT(*) as count FROM users;")
    if cursor.fetchone()["count"] == 0:
        pw_hash = hashlib.sha256("abc123".encode()).hexdigest()
        cursor.execute("""
        INSERT INTO users (username, password_hash, display_name, restaurant_name, location, cuisine_type, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("abc123", pw_hash, "Restaurant Owner", "My Restaurant", "Auto-detected", "Multi-Cuisine", "owner", now))

    conn.commit()
    conn.close()
    logger.info("Demo dataset successfully seeded.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data_if_empty()
    yield

# -------------------------------------------------------------------------
# FastAPI App Initialization
# -------------------------------------------------------------------------
app = FastAPI(
    title="Marginly - AI-Powered Menu Engineering & Recipe Costing",
    description="Standardize recipes, calculate deterministic costs and margins, and classify menu performance.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development: allow Vite frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# Pydantic Request / Response Models
# -------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    database: str
    local_ai: Dict[str, Any]
    restaurant_name: str
    currency: str

class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    base_unit: str = Field(..., pattern="^(g|kg|mg|ml|l|each|pcs|piece|unit)$")
    current_unit_price: float = Field(..., gt=0.0)
    currency: str = "INR"
    supplier: Optional[str] = None

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    base_unit: Optional[str] = None
    current_unit_price: Optional[float] = Field(None, gt=0.0)
    supplier: Optional[str] = None

class IngredientResponse(BaseModel):
    id: int
    name: str
    base_unit: str
    current_unit_price: float
    currency: str
    supplier: Optional[str] = None
    last_price_updated_at: str
    created_at: str

class RecipeLineInput(BaseModel):
    ingredient_id: Optional[int] = None
    quantity: float = Field(..., gt=0.0)
    unit: str
    waste_percent: float = Field(0.0, ge=0.0, lt=100.0)
    notes: Optional[str] = None

class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    source_text: Optional[str] = None
    servings_per_batch: float = Field(1.0, gt=0.0)
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    batch_overhead_cost: float = Field(0.0, ge=0.0)
    lines: List[RecipeLineInput] = []

class RecipeCostLineDetail(BaseModel):
    ingredient_id: Optional[int]
    ingredient_name: str
    entered_quantity: float
    entered_unit: str
    waste_percent: float
    effective_base_quantity: float
    base_unit: str
    unit_price: float
    line_cost: float

class RecipeCostResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    servings_per_batch: float
    batch_overhead_cost: float
    total_batch_cost: float
    cost_per_serving: float
    lines: List[RecipeCostLineDetail]

class RecipeInterpretRequest(BaseModel):
    source_text: str = Field(..., min_length=3)

class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: str = "Main Course"
    recipe_id: Optional[int] = None
    selling_price: float = Field(..., gt=0.0)
    currency: str = "INR"

class SalesImportLine(BaseModel):
    menu_item_name: str
    period: str = "Current Month"
    quantity_sold: int = Field(..., ge=0)
    channel: Optional[str] = "Dine-in"

class SalesImportRequest(BaseModel):
    records: List[SalesImportLine]

class AnalysisRequest(BaseModel):
    period: str = "Current Month"
    popularity_factor: Optional[float] = 1.0

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=3)
    display_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    location: Optional[str] = None
    cuisine_type: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    location: Optional[str] = None
    cuisine_type: Optional[str] = None
    role: str

# -------------------------------------------------------------------------
# Helper: Recipe Costing Engine (Deterministic)
# -------------------------------------------------------------------------
def compute_recipe_cost_for_id(recipe_id: int, conn: sqlite3.Connection) -> RecipeCostResponse:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE id = ?;", (recipe_id,))
    rec = cursor.fetchone()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recipe ID {recipe_id} not found")

    cursor.execute("""
        SELECT rl.*, i.name as ing_name, i.base_unit, i.current_unit_price
        FROM recipe_lines rl
        LEFT JOIN ingredients i ON rl.ingredient_id = i.id
        WHERE rl.recipe_id = ?;
    """, (recipe_id,))
    lines_db = cursor.fetchall()

    line_cost_decimals = []
    line_details = []

    for l in lines_db:
        ing_id = l["ingredient_id"]
        ing_name = l["ing_name"] or "Unlinked Ingredient"
        b_unit = l["base_unit"] or l["unit"]
        u_price = Decimal(str(l["current_unit_price"] or 0.0))

        qty_dec = Decimal(str(l["quantity"]))
        unit_str = l["unit"]
        waste_dec = Decimal(str(l["waste_percent"]))

        eff_base_qty, line_cost = calculate_ingredient_line_cost(
            quantity=qty_dec,
            unit=unit_str,
            base_unit=b_unit,
            current_unit_price=u_price,
            waste_percent=waste_dec
        )

        line_cost_decimals.append(line_cost)
        line_details.append(RecipeCostLineDetail(
            ingredient_id=ing_id,
            ingredient_name=ing_name,
            entered_quantity=float(qty_dec),
            entered_unit=unit_str,
            waste_percent=float(waste_dec),
            effective_base_quantity=float(round(eff_base_qty, 3)),
            base_unit=b_unit,
            unit_price=float(u_price),
            line_cost=float(round(line_cost, 2))
        ))

    servings = Decimal(str(rec["servings_per_batch"]))
    overhead = Decimal(str(rec["batch_overhead_cost"]))
    tot_batch, per_serving = calculate_recipe_cost(line_cost_decimals, servings, overhead)

    return RecipeCostResponse(
        recipe_id=rec["id"],
        recipe_name=rec["name"],
        servings_per_batch=float(servings),
        batch_overhead_cost=float(overhead),
        total_batch_cost=float(round(tot_batch, 2)),
        cost_per_serving=float(round(per_serving, 2)),
        lines=line_details
    )

# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health():
    ai_status = await check_lm_studio_health()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile WHERE id = 1;")
    prof = cursor.fetchone()
    conn.close()

    return HealthResponse(
        status="healthy",
        database="connected",
        local_ai=ai_status,
        restaurant_name=prof["restaurant_name"] if prof else settings.RESTAURANT_NAME,
        currency=prof["currency"] if prof else settings.DEFAULT_CURRENCY
    )

# --- Authentication ---
@app.post("/api/register")
def register(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = hashlib.sha256(user.password.encode()).hexdigest()
    try:
        cursor.execute("""
        INSERT INTO users (username, password_hash, display_name, restaurant_name, location, cuisine_type, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'owner', ?);
        """, (user.username.strip().lower(), pw_hash, user.display_name, user.restaurant_name, user.location, user.cuisine_type, now))
        conn.commit()
        user_id = cursor.lastrowid
        token = str(uuid.uuid4())
        cursor.execute("INSERT INTO auth_tokens (user_id, token, created_at) VALUES (?, ?, ?);", (user_id, token, now))
        conn.commit()
        conn.close()
        return {"token": token, "user": {"id": user_id, "username": user.username, "display_name": user.display_name, "restaurant_name": user.restaurant_name, "location": user.location, "cuisine_type": user.cuisine_type, "role": "owner"}}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already taken")

@app.post("/api/login")
def login(creds: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    pw_hash = hashlib.sha256(creds.password.encode()).hexdigest()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?;", (creds.username.strip().lower(), pw_hash))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = datetime.now(timezone.utc).isoformat()
    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO auth_tokens (user_id, token, created_at) VALUES (?, ?, ?);", (user["id"], token, now))
    conn.commit()
    conn.close()
    return {"token": token, "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "restaurant_name": user["restaurant_name"], "location": user["location"], "cuisine_type": user["cuisine_type"], "role": user["role"]}}

@app.get("/api/me")
def get_me(token: str = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT u.* FROM users u
    JOIN auth_tokens t ON t.user_id = u.id
    WHERE t.token = ?;
    """, (token,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "restaurant_name": user["restaurant_name"], "location": user["location"], "cuisine_type": user["cuisine_type"], "role": user["role"]}

@app.patch("/api/profile")
def update_profile(token: str = Query(...), updates: UserRegister = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM auth_tokens WHERE token = ?;", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = row["user_id"]
    if updates:
        cursor.execute("""
        UPDATE users SET display_name = COALESCE(?, display_name), restaurant_name = COALESCE(?, restaurant_name), location = COALESCE(?, location), cuisine_type = COALESCE(?, cuisine_type)
        WHERE id = ?;
        """, (updates.display_name, updates.restaurant_name, updates.location, updates.cuisine_type, user_id))
        conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "restaurant_name": user["restaurant_name"], "location": user["location"], "cuisine_type": user["cuisine_type"], "role": user["role"]}

# --- Ingredients ---
@app.get("/api/ingredients", response_model=List[IngredientResponse])
def list_ingredients():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredients ORDER BY name ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(ing: IngredientCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute("""
        INSERT INTO ingredients (name, base_unit, current_unit_price, currency, supplier, last_price_updated_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (ing.name.strip(), ing.base_unit.lower(), ing.current_unit_price, ing.currency, ing.supplier, now, now))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM ingredients WHERE id = ?;", (new_id,))
        created = cursor.fetchone()
        conn.close()
        return dict(created)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Ingredient with name '{ing.name}' already exists.")

@app.patch("/api/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(ingredient_id: int, updates: IngredientUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredients WHERE id = ?;", (ingredient_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        raise HTTPException(status_code=404, detail="Ingredient not found")

    now = datetime.now(timezone.utc).isoformat()
    old_price = current["current_unit_price"]

    new_price = updates.current_unit_price if updates.current_unit_price is not None else old_price
    new_name = updates.name.strip() if updates.name is not None else current["name"]
    new_unit = updates.base_unit.lower() if updates.base_unit is not None else current["base_unit"]
    new_supplier = updates.supplier if updates.supplier is not None else current["supplier"]

    # Price change check & alert creation
    if updates.current_unit_price is not None and abs(new_price - old_price) > 1e-6:
        change_pct = ((new_price - old_price) / old_price) * 100.0
        cursor.execute("""
        INSERT INTO ingredient_price_history (ingredient_id, old_price, new_price, change_percentage, updated_at)
        VALUES (?, ?, ?, ?, ?);
        """, (ingredient_id, old_price, new_price, change_pct, now))

        if abs(change_pct) >= settings.PRICE_ALERT_THRESHOLD_PERCENT:
            direction = "surged by" if change_pct > 0 else "decreased by"
            severity = "warning" if change_pct > 0 else "info"
            alert_msg = (
                f"Price of '{new_name}' {direction} {abs(change_pct):.1f}% "
                f"(₹{old_price:.3f} -> ₹{new_price:.3f} per {new_unit}). "
                f"Check linked recipes and menu margins!"
            )
            cursor.execute("""
            INSERT INTO alerts (alert_type, severity, message, item_id, created_at)
            VALUES (?, ?, ?, ?, ?);
            """, ("PRICE_SPIKE", severity, alert_msg, ingredient_id, now))

    cursor.execute("""
    UPDATE ingredients
    SET name = ?, base_unit = ?, current_unit_price = ?, supplier = ?, last_price_updated_at = ?
    WHERE id = ?;
    """, (new_name, new_unit, new_price, new_supplier, now, ingredient_id))

    conn.commit()
    cursor.execute("SELECT * FROM ingredients WHERE id = ?;", (ingredient_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

# --- Recipes ---
@app.get("/api/recipes")
def list_recipes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes ORDER BY id DESC;")
    recipes = cursor.fetchall()

    result = []
    for r in recipes:
        cost_info = compute_recipe_cost_for_id(r["id"], conn)
        item = dict(r)
        item["total_batch_cost"] = cost_info.total_batch_cost
        item["cost_per_serving"] = cost_info.cost_per_serving
        result.append(item)

    conn.close()
    return result

@app.post("/api/recipes", status_code=status.HTTP_201_CREATED)
def create_recipe(rec: RecipeCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    INSERT INTO recipes (name, description, source_text, servings_per_batch, yield_quantity, yield_unit, batch_overhead_cost, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?);
    """, (rec.name, rec.description, rec.source_text, rec.servings_per_batch, rec.yield_quantity, rec.yield_unit, rec.batch_overhead_cost, now, now))
    rec_id = cursor.lastrowid

    for line in rec.lines:
        cursor.execute("""
        INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent, notes)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (rec_id, line.ingredient_id, line.quantity, line.unit.lower(), line.waste_percent, line.notes))

    conn.commit()
    cost_info = compute_recipe_cost_for_id(rec_id, conn)
    conn.close()
    return cost_info

@app.get("/api/recipes/{recipe_id}/cost", response_model=RecipeCostResponse)
def get_recipe_cost(recipe_id: int):
    conn = get_db_connection()
    cost_info = compute_recipe_cost_for_id(recipe_id, conn)
    conn.close()
    return cost_info

@app.post("/api/recipes/interpret", response_model=RecipeDraftResponse)
async def interpret_recipe(req: RecipeInterpretRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM ingredients;")
    catalog_names = [row["name"] for row in cursor.fetchall()]
    conn.close()

    draft = await interpret_recipe_text(req.source_text, catalog_names)
    return draft

# --- Menu Items ---
@app.get("/api/menu-items")
def list_menu_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, r.name as recipe_name
        FROM menu_items m
        LEFT JOIN recipes r ON m.recipe_id = r.id
        ORDER BY m.id ASC;
    """)
    items = cursor.fetchall()

    result = []
    for item in items:
        cost_per_serving = 0.0
        if item["recipe_id"]:
            try:
                c = compute_recipe_cost_for_id(item["recipe_id"], conn)
                cost_per_serving = c.cost_per_serving
            except Exception:
                pass

        cm = item["selling_price"] - cost_per_serving
        margin_pct = (cm / item["selling_price"] * 100.0) if item["selling_price"] > 0 else 0.0

        d = dict(item)
        d["cost_per_serving"] = cost_per_serving
        d["contribution_margin"] = round(cm, 2)
        d["margin_percentage"] = round(margin_pct, 1)
        result.append(d)

    conn.close()
    return result

@app.post("/api/menu-items", status_code=status.HTTP_201_CREATED)
def create_menu_item(m: MenuItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO menu_items (name, category, recipe_id, selling_price, currency, created_at)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (m.name.strip(), m.category.strip(), m.recipe_id, m.selling_price, m.currency, now))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "name": m.name, "selling_price": m.selling_price}

# --- Sales Import ---
@app.post("/api/sales/import")
def import_sales(req: SalesImportRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    imported_count = 0
    errors = []

    for line in req.records:
        cursor.execute("SELECT id FROM menu_items WHERE LOWER(name) = LOWER(?);", (line.menu_item_name.strip(),))
        row = cursor.fetchone()
        if not row:
            errors.append(f"Menu item '{line.menu_item_name}' not found.")
            continue

        item_id = row["id"]
        cursor.execute("""
        INSERT INTO sales_records (menu_item_id, period, quantity_sold, channel, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(menu_item_id, period, channel) DO UPDATE SET
            quantity_sold = excluded.quantity_sold,
            created_at = excluded.created_at;
        """, (item_id, line.period.strip(), line.quantity_sold, line.channel, now))
        imported_count += 1

    conn.commit()
    conn.close()
    return {"imported": imported_count, "errors": errors}

# --- Menu Engineering Analysis ---
@app.post("/api/analysis", response_model=MenuAnalysisSummary)
def analyze_menu(req: AnalysisRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id, m.name, m.category, m.recipe_id, m.selling_price,
               COALESCE(s.quantity_sold, 0) as quantity_sold
        FROM menu_items m
        LEFT JOIN sales_records s ON s.menu_item_id = m.id AND s.period = ?
        WHERE m.is_active = 1;
    """, (req.period,))
    items_db = cursor.fetchall()

    raw_items_list = []
    for row in items_db:
        cost = 0.0
        if row["recipe_id"]:
            try:
                c = compute_recipe_cost_for_id(row["recipe_id"], conn)
                cost = c.cost_per_serving
            except Exception:
                cost = 0.0

        raw_items_list.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "selling_price": row["selling_price"],
            "cost_per_serving": cost,
            "quantity_sold": row["quantity_sold"]
        })

    conn.close()

    summary = compute_menu_engineering_matrix(
        items_data=raw_items_list,
        popularity_factor=req.popularity_factor or 1.0,
        comparison_scope_name=req.period
    )
    return summary

# --- AI Recommendations Endpoint ---
@app.post("/api/recommendations", response_model=MenuRecommendationsResponse)
async def get_recommendations(req: AnalysisRequest):
    # First calculate deterministic summary
    summary = analyze_menu(req)
    # Then query Qwen for recommendations (or return deterministic rules fallback)
    recs = await generate_menu_recommendations(summary.model_dump(), currency_symbol=settings.DEFAULT_CURRENCY_SYMBOL)
    return recs

# --- Alerts & Price History ---
@app.get("/api/alerts")
def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 20;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
