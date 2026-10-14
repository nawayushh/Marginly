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
import hashlib
import uuid
import re
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException, status, Query, Request, File, UploadFile, Form
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
    get_market_insights,
    fallback_market_insights,
    RecipeDraftResponse,
    MenuRecommendationsResponse,
    MarketInsightsResponse,
    check_realtime_mandi_alerts,
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
        phone TEXT,
        restaurant_type TEXT,
        daily_covers INTEGER,
        sourcing_model TEXT,
        signature_dish TEXT,
        role TEXT NOT NULL DEFAULT 'owner',
        created_at TEXT NOT NULL
    );
    """)

    # Ensure all columns exist for existing databases
    for col, col_type in [
        ("phone", "TEXT"),
        ("restaurant_type", "TEXT"),
        ("daily_covers", "INTEGER"),
        ("sourcing_model", "TEXT"),
        ("signature_dish", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type};")
        except sqlite3.OperationalError:
            pass

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
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?;", ("abc123",))
    if not cursor.fetchone():
        pw_hash = hashlib.sha256("abc123".encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO users (
            username, password_hash, display_name, restaurant_name, location,
            cuisine_type, phone, restaurant_type, daily_covers, sourcing_model,
            signature_dish, role, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "abc123",
            pw_hash,
            "Demo Chef",
            "Café Doon Brew",
            "Rajpur Rd, Dehradun",
            "Café & Continental",
            "+91 98765 43210",
            "Café & Bistro",
            120,
            "Local Mandi",
            "Signature Cold Coffee",
            "owner",
            now
        ))
        conn.commit()
    conn.close()

def seed_demo_data_if_empty():
    # Keep database at clean slate with 0 dishes, 0 recipes, 0 sales until user enters them
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_default_user()
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
    current_unit_price: float = Field(..., ge=0.0)  # ge=0.0 allows ₹0 for self-grown / in-house items
    currency: str = "INR"
    supplier: Optional[str] = None

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    base_unit: Optional[str] = None
    current_unit_price: Optional[float] = Field(None, ge=0.0)
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
    name: Optional[str] = None
    quantity: float = Field(..., gt=0.0)
    unit: str
    waste_percent: float = Field(0.0, ge=0.0, lt=100.0)
    unit_price: Optional[float] = None
    is_self_grown: Optional[bool] = False
    notes: Optional[str] = None

class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: Optional[str] = "Main Course"
    selling_price: Optional[float] = None
    description: Optional[str] = None
    source_text: Optional[str] = None
    servings_per_batch: float = Field(1.0, gt=0.0)
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    batch_overhead_cost: float = Field(0.0, ge=0.0)
    lines: List[RecipeLineInput] = []
    ingredients: Optional[List[Dict[str, Any]]] = None

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
    phone: Optional[str] = None
    restaurant_type: Optional[str] = None
    daily_covers: Optional[Union[str, int]] = None
    sourcing_model: Optional[str] = None
    signature_dish: Optional[str] = None

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
    phone: Optional[str] = None
    restaurant_type: Optional[str] = None
    daily_covers: Optional[int] = None
    sourcing_model: Optional[str] = None
    signature_dish: Optional[str] = None
    role: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    location: Optional[str] = None
    cuisine_type: Optional[str] = None
    phone: Optional[str] = None
    restaurant_type: Optional[str] = None
    daily_covers: Optional[int] = None
    sourcing_model: Optional[str] = None
    signature_dish: Optional[str] = None

class MarketInsightsRequest(BaseModel):
    location: Optional[str] = "Dehradun / Delhi NCR"
    cuisine_type: Optional[str] = "Multi-Cuisine"
    restaurant_type: Optional[str] = "Dine-in"

class MarketImportRequest(BaseModel):
    location: Optional[str] = "Dehradun / Delhi NCR"
    city: Optional[str] = None
    cuisine_type: Optional[str] = "Multi-Cuisine"
    restaurant_type: Optional[str] = "Dine-in"
    ingredients: Optional[List[Dict[str, Any]]] = None
    dishes: Optional[List[Dict[str, Any]]] = None

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
        covers_val = 100
        if isinstance(user.daily_covers, int):
            covers_val = user.daily_covers
        elif isinstance(user.daily_covers, str):
            digits = re.findall(r'\d+', user.daily_covers)
            if digits:
                covers_val = int(digits[-1])

        cursor.execute("""
        INSERT INTO users (username, password_hash, display_name, restaurant_name, location, cuisine_type, phone, restaurant_type, daily_covers, sourcing_model, signature_dish, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'owner', ?);
        """, (
            user.username.strip().lower(),
            pw_hash,
            user.display_name or user.username,
            user.restaurant_name or "My Restaurant",
            user.location or "Local Mandi Hub",
            user.cuisine_type or "Multi-Cuisine",
            user.phone,
            user.restaurant_type or "Dine-in",
            covers_val,
            user.sourcing_model or "Local Mandi",
            user.signature_dish or "Chef's Special",
            now
        ))
        conn.commit()
        user_id = cursor.lastrowid
        token = str(uuid.uuid4())
        cursor.execute("INSERT INTO auth_tokens (user_id, token, created_at) VALUES (?, ?, ?);", (user_id, token, now))
        conn.commit()
        conn.close()
        return {
            "token": token,
            "user": {
                "id": user_id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "restaurant_name": user.restaurant_name or "My Restaurant",
                "location": user.location or "Local Mandi Hub",
                "cuisine_type": user.cuisine_type or "Multi-Cuisine",
                "phone": user.phone,
                "restaurant_type": user.restaurant_type or "Dine-in",
                "daily_covers": user.daily_covers or 100,
                "sourcing_model": user.sourcing_model or "Local Mandi",
                "signature_dish": user.signature_dish or "Chef's Special",
                "role": "owner"
            }
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already taken")

@app.post("/api/login")
def login(creds: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    pw_hash = hashlib.sha256(creds.password.encode()).hexdigest()
    login_id = creds.username.strip().lower()
    cursor.execute("""
        SELECT * FROM users 
        WHERE (LOWER(username) = ? OR LOWER(phone) = ? OR LOWER(display_name) = ?) 
          AND password_hash = ?;
    """, (login_id, login_id, login_id, pw_hash))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = datetime.now(timezone.utc).isoformat()
    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO auth_tokens (user_id, token, created_at) VALUES (?, ?, ?);", (user["id"], token, now))
    conn.commit()
    conn.close()
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "restaurant_name": user["restaurant_name"],
            "location": user["location"],
            "cuisine_type": user["cuisine_type"],
            "phone": user["phone"] if "phone" in user.keys() else None,
            "restaurant_type": user["restaurant_type"] if "restaurant_type" in user.keys() else "Dine-in",
            "daily_covers": user["daily_covers"] if "daily_covers" in user.keys() else 100,
            "sourcing_model": user["sourcing_model"] if "sourcing_model" in user.keys() else "Local Mandi",
            "signature_dish": user["signature_dish"] if "signature_dish" in user.keys() else None,
            "role": user["role"]
        }
    }

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
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "restaurant_name": user["restaurant_name"],
        "location": user["location"],
        "cuisine_type": user["cuisine_type"],
        "phone": user["phone"] if "phone" in user.keys() else None,
        "restaurant_type": user["restaurant_type"] if "restaurant_type" in user.keys() else "Dine-in",
        "daily_covers": user["daily_covers"] if "daily_covers" in user.keys() else 100,
        "sourcing_model": user["sourcing_model"] if "sourcing_model" in user.keys() else "Local Mandi",
        "signature_dish": user["signature_dish"] if "signature_dish" in user.keys() else None,
        "role": user["role"]
    }

@app.patch("/api/profile")
def update_profile(token: str = Query(...), updates: UserUpdate = None):
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
        UPDATE users SET 
            display_name = COALESCE(?, display_name), 
            restaurant_name = COALESCE(?, restaurant_name), 
            location = COALESCE(?, location), 
            cuisine_type = COALESCE(?, cuisine_type),
            phone = COALESCE(?, phone),
            restaurant_type = COALESCE(?, restaurant_type),
            daily_covers = COALESCE(?, daily_covers),
            sourcing_model = COALESCE(?, sourcing_model),
            signature_dish = COALESCE(?, signature_dish)
        WHERE id = ?;
        """, (
            updates.display_name,
            updates.restaurant_name,
            updates.location,
            updates.cuisine_type,
            updates.phone,
            updates.restaurant_type,
            updates.daily_covers,
            updates.sourcing_model,
            updates.signature_dish,
            user_id
        ))
        conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "restaurant_name": user["restaurant_name"],
        "location": user["location"],
        "cuisine_type": user["cuisine_type"],
        "phone": user["phone"] if "phone" in user.keys() else None,
        "restaurant_type": user["restaurant_type"] if "restaurant_type" in user.keys() else "Dine-in",
        "daily_covers": user["daily_covers"] if "daily_covers" in user.keys() else 100,
        "sourcing_model": user["sourcing_model"] if "sourcing_model" in user.keys() else "Local Mandi",
        "signature_dish": user["signature_dish"] if "signature_dish" in user.keys() else None,
        "role": user["role"]
    }

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

    # Gather lines: from rec.lines or rec.ingredients
    resolved_lines = list(rec.lines)
    if not resolved_lines and rec.ingredients:
        for ing in rec.ingredients:
            resolved_lines.append(RecipeLineInput(
                ingredient_id=ing.get("ingredient_id"),
                name=ing.get("name"),
                quantity=float(ing.get("quantity", 1.0)),
                unit=ing.get("unit", "g"),
                waste_percent=float(ing.get("waste_percent", 0.0)),
                unit_price=float(ing.get("unit_price", 0.0)) if ing.get("unit_price") is not None else None,
                is_self_grown=bool(ing.get("is_self_grown", False))
            ))

    for line in resolved_lines:
        ing_id = line.ingredient_id
        if not ing_id and line.name:
            # Check if ingredient exists by name
            cursor.execute("SELECT id FROM ingredients WHERE LOWER(name) = ?;", (line.name.strip().lower(),))
            row = cursor.fetchone()
            if row:
                ing_id = row["id"]
            else:
                # Create ingredient
                u_str = line.unit.lower()
                stored_unit = "g" if u_str in ["g", "kg", "mg"] else ("ml" if u_str in ["ml", "l"] else u_str)
                price_val = 0.0 if line.is_self_grown else (line.unit_price or 10.0)
                if stored_unit in ["g", "ml"]:
                    if u_str in ["kg", "l"] or price_val > 5.0:
                        unit_price_calc = price_val / 1000.0
                    else:
                        unit_price_calc = price_val
                else:
                    unit_price_calc = price_val

                cursor.execute("""
                INSERT INTO ingredients (name, base_unit, current_unit_price, supplier, last_price_updated_at, created_at)
                VALUES (?, ?, ?, 'Recipe Direct Input', ?, ?);
                """, (line.name.strip(), stored_unit, unit_price_calc, now, now))
                ing_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO recipe_lines (recipe_id, ingredient_id, quantity, unit, waste_percent, notes)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (rec_id, ing_id, line.quantity, line.unit.lower(), line.waste_percent, line.notes))

    # If selling_price is provided, create/link menu_item and seed starter sales record
    if rec.selling_price is not None and rec.selling_price > 0:
        cursor.execute("""
        INSERT INTO menu_items (name, category, recipe_id, selling_price, created_at)
        VALUES (?, ?, ?, ?, ?);
        """, (rec.name, rec.category or "Main Course", rec_id, rec.selling_price, now))
        menu_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO sales_records (menu_item_id, period, quantity_sold, channel, created_at)
        VALUES (?, 'Current Month', ?, 'Dine-in', ?)
        ON CONFLICT(menu_item_id, period, channel) DO NOTHING;
        """, (menu_id, 120, now))

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

@app.post("/api/recipes/transcribe-audio")
async def transcribe_recipe_audio(request: Request):
    content_type = request.headers.get("content-type", "")
    dialect = request.query_params.get("dialect", "hi-IN")
    wav_bytes = b""
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("audio") or form.get("file")
        if audio_file and hasattr(audio_file, "read"):
            wav_bytes = await audio_file.read()
        dialect = str(form.get("dialect", dialect))
    elif "application/json" in content_type:
        try:
            data = await request.json()
            b64 = data.get("audio_base64", "")
            if b64:
                import base64
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                wav_bytes = base64.b64decode(b64)
            dialect = data.get("dialect", dialect)
        except Exception:
            pass
    else:
        wav_bytes = await request.body()

    if not wav_bytes or len(wav_bytes) < 44:
        raise HTTPException(status_code=400, detail="Empty or invalid audio data received")

    import speech_recognition as sr
    import io

    r = sr.Recognizer()
    transcript = ""

    try:
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio_data = r.record(source)
            try:
                # Try requested dialect first (hi-IN or en-IN)
                transcript = r.recognize_google(audio_data, language=dialect)
            except sr.UnknownValueError:
                # Try fallback dialect
                alt_dialect = "en-IN" if dialect == "hi-IN" else "hi-IN"
                try:
                    transcript = r.recognize_google(audio_data, language=alt_dialect)
                except Exception:
                    transcript = ""
    except Exception as e:
        logger.warning(f"Audio transcription recognition error: {e}")

    if not transcript:
        return {
            "success": False,
            "transcript": "",
            "message": "No clear speech detected. Speak closer to the microphone or try again.",
            "recipe": None
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM ingredients;")
    catalog_names = [row["name"] for row in cursor.fetchall()]
    conn.close()

    draft = await interpret_recipe_text(transcript, catalog_names)
    not_on_menu = [
        ing.matched_ingredient_name for ing in draft.ingredients 
        if ing.notes and "NOT ON MENU" in ing.notes
    ]
    return {
        "success": True,
        "transcript": transcript,
        "dialect": dialect,
        "recipe": draft,
        "not_on_menu": not_on_menu
    }

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
# --- Market Intelligence & Regional Pricing ---
@app.post("/api/market-insights", response_model=MarketInsightsResponse)
async def fetch_market_insights(req: MarketInsightsRequest):
    insights = await get_market_insights(
        location=req.location or "Dehradun / Delhi NCR",
        cuisine_type=req.cuisine_type or "Multi-Cuisine",
        restaurant_type=req.restaurant_type or "Dine-in"
    )
    return insights

@app.post("/api/market-insights/import")
def import_market_starter_package(req: MarketImportRequest):
    """
    Imports the curated regional ingredients and starter dishes into the SQLite database,
    allowing the user to begin calculations immediately without manual entry.
    Supports ₹0 unit price for home-grown/self-produced ingredients.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    imported_ingredients = 0
    imported_dishes = 0

    ingredients_to_import = req.ingredients
    dishes_to_import = req.dishes

    if not ingredients_to_import and not dishes_to_import:
        resolved_loc = req.location or req.city or "Dehradun / Delhi NCR"
        resolved_cuisine = req.cuisine_type or "Multi-Cuisine"
        gen = fallback_market_insights(resolved_loc, resolved_cuisine, req.restaurant_type or "Dine-in")
        ingredients_to_import = [
            {"name": i.name, "base_unit": i.base_unit, "market_price": i.market_price, "is_homegrown": False}
            for i in gen.ingredients
        ]
        dishes_to_import = [
            {"name": d.name, "category": d.category, "suggested_selling_price": d.suggested_selling_price, "estimated_plate_cost": d.estimated_plate_cost, "description": d.description}
            for d in gen.starter_dishes
        ]

    # 1. Import Ingredients if provided
    if ingredients_to_import:
        for ing in ingredients_to_import:
            name = ing.get("name", "").strip()
            if not name:
                continue
            base_unit = ing.get("base_unit", "kg").lower()
            price = float(ing.get("market_price", 0.0))

            # Convert to base unit pricing (g, ml, each)
            if base_unit == "kg":
                unit_price = price / 1000.0
                stored_unit = "g"
            elif base_unit == "l":
                unit_price = price / 1000.0
                stored_unit = "ml"
            else:
                unit_price = price
                stored_unit = base_unit

            # If user marked as self-grown/home-grown, allow price to be 0
            if ing.get("is_homegrown", False):
                unit_price = 0.0

            cursor.execute("""
            INSERT INTO ingredients (name, base_unit, current_unit_price, supplier, last_price_updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                current_unit_price = excluded.current_unit_price,
                last_price_updated_at = excluded.last_price_updated_at;
            """, (name, stored_unit, unit_price, f"{req.location} Mandi Benchmark", now, now))
            imported_ingredients += 1

    # 2. Import Starter Dishes if provided
    if dishes_to_import:
        for d in dishes_to_import:
            d_name = d.get("name", "").strip()
            if not d_name:
                continue
            cat = d.get("category", "Main Course")
            sp = float(d.get("suggested_selling_price", 150.0))
            plate_cost = float(d.get("estimated_plate_cost", 40.0))
            desc = d.get("description", "")

            # Create standard recipe draft
            cursor.execute("""
            INSERT INTO recipes (name, description, servings_per_batch, batch_overhead_cost, status, created_at, updated_at)
            VALUES (?, ?, 1.0, 5.0, 'confirmed', ?, ?);
            """, (d_name, desc, now, now))
            rec_id = cursor.lastrowid

            # Create menu item
            cursor.execute("""
            INSERT INTO menu_items (name, category, recipe_id, selling_price, created_at)
            VALUES (?, ?, ?, ?, ?);
            """, (d_name, cat, rec_id, sp, now))
            menu_id = cursor.lastrowid

            # Seed realistic starter sales record
            cursor.execute("""
            INSERT INTO sales_records (menu_item_id, period, quantity_sold, channel, created_at)
            VALUES (?, 'Current Month', ?, 'Dine-in', ?)
            ON CONFLICT(menu_item_id, period, channel) DO NOTHING;
            """, (menu_id, 120, now))
            imported_dishes += 1

    conn.commit()
    conn.close()
    return {
        "status": "success",
        "imported_ingredients": imported_ingredients,
        "imported_dishes": imported_dishes,
        "message": f"Successfully initialized {imported_dishes} starter dishes and {imported_ingredients} ingredients with regional mandi rates!"
    }

@app.get("/api/alerts")
def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 20;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/alerts/sync-live-mandi")
@app.post("/api/alerts/check-mandi")
async def sync_live_mandi(payload: Dict[str, Any] = None):
    location = "Dehradun / Delhi NCR"
    if payload and isinstance(payload, dict):
        location = payload.get("location") or location
    
    alerts_data = await check_realtime_mandi_alerts(location)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    
    synced_alerts = []
    for item in alerts_data:
        commodity = item.get("commodity", "Ingredient")
        direction = item.get("direction", "SPIKE")
        change_pct = float(item.get("change_percent", 0.0))
        rate = float(item.get("market_price", 0.0))
        unit = item.get("unit", "kg")
        severity = item.get("severity", "warning")
        reason = item.get("impact_reason", "")
        
        msg = f"{commodity} wholesale mandi rate {direction.lower()} by {abs(change_pct):.1f}% (₹{rate}/{unit}). {reason}"
        
        # Check if identical alert already exists to prevent duplicate spam
        cursor.execute("SELECT id FROM alerts WHERE message = ?;", (msg,))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
            INSERT INTO alerts (alert_type, severity, message, item_id, created_at)
            VALUES (?, ?, ?, NULL, ?);
            """, ("PRICE_SPIKE", severity, msg, now))
            alert_id = cursor.lastrowid
        else:
            alert_id = existing["id"]
            
        synced_alerts.append({
            "id": alert_id,
            "commodity": commodity,
            "direction": direction,
            "change_percent": change_pct,
            "market_price": rate,
            "unit": unit,
            "severity": severity,
            "message": msg,
            "created_at": now
        })
        
    conn.commit()
    conn.close()
    return {"status": "success", "alerts": synced_alerts, "count": len(synced_alerts)}

@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE id = ?;", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted_id": alert_id}

@app.post("/api/alerts/clear")
def clear_all_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts;")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "All alerts cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
