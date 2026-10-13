# Marginly

### AI-Powered Menu Profitability Analyzer

Marginly helps restaurants understand menu performance by analyzing dish popularity and contribution margins, turning sales data into actionable business insights.

## Features

- **Performance Analytics:** Track revenue, ingredient costs, and contribution profit.
- **Menu Engineering:** Classify dishes as Stars, Plowhorses, Puzzles, or Dogs.
- **AI-Powered Insights:** Generate data-driven recommendations using Qwen 3.5 9B.
- **Menu Management:** Organize and analyze menu items.
- **Local AI Inference:** Run Qwen through LM Studio.

## How It Works

1. Input menu items, selling prices, ingredient costs, and quantities sold.
2. Calculate financial metrics using Python.
3. Classify dishes based on popularity and contribution margin.
4. Use AI to identify patterns and suggest improvements.

## Tech Stack

- **Frontend:** CSS Tailwind, React
- **Backend:** Python, FastAPI
- **AI:** Qwen 3.5 9B, LM Studio, OpenAI SDK
- **Visualization:** Chart.js

## Core Metrics

- Contribution Margin = Selling Price − Ingredient Cost
- Revenue = Selling Price × Quantity Sold
- Contribution Profit = Contribution Margin × Quantity Sold
- Popularity = Dish Quantity Sold ÷ Total Units Sold

## Local Setup

1. Install Python, Node.js, and [LM Studio](https://lmstudio.ai/).

2. Load Qwen 3.5 9B and start the LM Studio server on port `1235`.

3. Install backend dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

4. Start the backend using the project's configured FastAPI command.

5. Install frontend dependencies and start the Vite development server:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Configure the LM Studio endpoint as `http://localhost:1235/v1` in the backend environment.

## Project Goal

Marginly combines reliable financial calculations with AI-generated insights to help restaurant owners make more informed decisions about pricing, promotions, and menu performance.

**Know your menu. Understand your margins.**
