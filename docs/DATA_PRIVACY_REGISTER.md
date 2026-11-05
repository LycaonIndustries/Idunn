# Data Privacy Register & Personal Data Inventory

*Compliant with European Union General Data Protection Regulation (GDPR Article 30) and India Digital Personal Data Protection Act (DPDP Act 2023).*

## 1. Overview & Data Controller
- **System**: Iðunn Kitchen OS
- **Controller**: Lycaon Industries
- **Scope**: Home kitchen inventory management, receipt ingestion, multimodal recipe vault, and weekly meal planning.

---

## 2. Personal Data Mapping & Processing Register

| Category | Data Elements | Processing Purpose | Legal Basis | Storage Location | Retention / Erasure Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication & Identity** | Email address, User ID (`sub`) | Account access, tenant data isolation | Contract performance | Supabase Auth / Local JWT | Deleted immediately upon account erasure. |
| **Pantry Inventory** | Item name, quantity, unit, location, expiry date | Waste reduction, expiry alerts, pantry gap matching | User consent / Legitimate interest | `items` collection | Deleted immediately upon account erasure or item consumption. |
| **Recipe Vault** | Custom recipe titles, notes, personal steps | Personal cookbook, cooking guidance | User consent | `recipes` collection | Deleted immediately upon account erasure or manual recipe deletion. |
| **Grocery Receipts** | Store name, purchase date, line items, receipt image URI | Automated pantry stock ingestion | User consent | `receipts` collection | Deleted immediately upon account erasure. Images purged on user request. |
| **Weekly Meal Plans** | Scheduled recipes, slot assignments, serving multipliers | Household meal coordination | User consent | `meal_plans` collection | Deleted immediately upon account erasure. |
| **Shopping Lists** | Required ingredients, purchased check state | Grocery shopping assistance | User consent | `shopping_lists` collection | Deleted immediately upon account erasure or when cleared. |
| **AI Token Usage Logs** | Request timestamp, prompt token count, completion token count | Rate limiting, quota enforcement | Legitimate interest | `ai_usage` collection | Purged after 90 days rolling window or immediately on account erasure. |

---

## 3. Data Subject Rights & Endpoints

- **Right to Erasure (Article 17 GDPR / Section 12 DPDP)**:
  `DELETE /api/v1/users/me` triggers a synchronous cascade deletion purging all items, recipes, receipts, meal plans, shopping lists, and AI logs.
- **Right to Data Portability (Article 20 GDPR / Section 11 DPDP)**:
  `GET /api/v1/users/me/export` generates a comprehensive machine-readable JSON archive containing all user entities.
- **Right to Rectification (Article 16 GDPR)**:
  Available in-app via inline CRUD endpoints across inventory, recipes, and meal plans.
