# Product Categories for Receipt Classification

This document contains a comprehensive and balanced list of **categories in English**, suitable for supermarkets, grocery stores, and household goods shops (e.g., Lidl, Carrefour, DM, Maxi, Rossmann).  
It can be used as a reference taxonomy for categorizing receipt items in data extraction and analysis systems.

---

## 🥦 1. Food & Groceries (Продукты питания)

### 🥩 Meat & Fish
- **Fresh Meat** (beef, pork, chicken, turkey, etc.)
- **Processed Meat & Sausages** (ham, bacon, salami, wurst, etc.)
- **Fish & Seafood** (fresh or frozen fish, shrimp, tuna, etc.)

### 🧀 Dairy & Eggs
- **Milk & Cream**
- **Yogurt & Kefir**
- **Cheese** (mozzarella, feta, processed cheese, etc.)
- **Butter & Margarine**
- **Eggs**

### 🥖 Bakery & Bread
- **Bread** (white, whole grain, rye, baguette, etc.)
- **Pastries** (croissants, buns, muffins)
- **Cakes & Desserts** (ready-made desserts, pies, etc.)

### 🍎 Fruits & Vegetables
- **Fresh Fruits**
- **Fresh Vegetables**
- **Frozen Fruits & Vegetables**
- **Salads & Greens**
- **Herbs & Spices (fresh)**

### 🧂 Pantry & Dry Goods
- **Flour & Baking Ingredients**
- **Pasta, Rice & Grains**
- **Canned & Jarred Goods**
- **Spices & Seasonings**
- **Sauces & Condiments** (ketchup, mustard, mayo, etc.)
- **Cooking Oils & Vinegar**

### 🍫 Sweets & Snacks
- **Chocolate & Candy**
- **Biscuits & Cookies**
- **Chips & Savory Snacks**
- **Nuts & Dried Fruits**
- **Breakfast Cereals & Granola**
- **Ice Cream**

### 🍽️ Ready Meals & Frozen Foods
- **Ready-to-Eat Meals** (microwave dishes, salads, sandwiches)
- **Frozen Meals & Pizzas**
- **Frozen Pastries**

---

## ☕ 2. Beverages (Напитки)
- **Water** (still, sparkling)
- **Soft Drinks & Juices**
- **Coffee & Tea**
- **Energy Drinks**
- **Alcoholic Beverages** (beer, wine, spirits)

---

## 🧴 3. Personal Care & Hygiene (Средства личной гигиены)
- **Toothpaste & Oral Care**
- **Soap & Shower Gels**
- **Shampoos & Hair Care**
- **Deodorants**
- **Skin Care** (creams, lotions)
- **Cosmetics & Makeup**
- **Shaving Products**
- **Feminine Hygiene** (pads, tampons)
- **Baby Care Products** (baby shampoo, wipes, diapers)

---

## 🧽 4. Household & Cleaning (Бытовая химия)
- **Laundry Detergents**
- **Fabric Softeners**
- **Dishwashing Products**
- **Surface Cleaners & Sprays**
- **Bathroom & Toilet Cleaners**
- **Air Fresheners**
- **Paper Products** (toilet paper, paper towels, napkins)
- **Garbage Bags**
- **Sponges & Cleaning Accessories**

---

## 🐾 5. Pet Products
- **Pet Food (Dog, Cat, etc.)**
- **Pet Treats**
- **Pet Care & Accessories**

---

## 🏠 6. Home & Miscellaneous
- **Kitchen Supplies** (foil, cling film, baking paper)
- **Tableware & Utensils**
- **Batteries & Light Bulbs**
- **Seasonal Items (e.g. Christmas, Easter)**
- **Stationery & Small Office Supplies**

---

## 💊 7. Health & Pharmacy
- **Vitamins & Supplements**
- **Medicines & Pain Relief** (OTC)
- **First Aid** (bandages, antiseptics)
- **Medical Devices** (thermometers, tests)

---

## 🧳 8. Non-Food / Misc. Retail
- **Perfumes & Fragrances**
- **Hair Styling Tools & Accessories**
- **Home Fragrance & Candles**
- **Travel Size Products**
- **Gift Sets & Small Accessories**

---

## 📊 9. Other / Unclassified
- **Unknown** (fallback category if not recognized)
- **Services** (deposit return, delivery, etc.)
- **Deposits / Returns** (bottle deposit “Pfand”)

---

### 💡 Usage Tips
- Store this list as JSON or CSV for keyword-based classification.
- For DM/Lidl/Maxi, consider local brand mapping (e.g., *Balea → Hygiene*, *Alnatura → Organic Food*).
- You can use a **two-level classification system**:
  1. `category_group` → Food / Hygiene / Cleaning  
  2. `category_sub` → Dairy / Sweets / Laundry Detergents
