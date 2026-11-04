/**
 * Core TypeScript type definitions for the Iðunn Kitchen OS frontend.
 * Provides data contracts matching FastAPI backend schemas.
 */

// Model ingredient items with optional quantities and regional units.
// Quantities can be null when recipes describe unmeasured ingredients (e.g. "salt to taste").
export interface IngredientItem {
  /** Name of the ingredient. */
  name: string
  /** Numeric quantity required. Null if unmeasured. */
  quantity?: number | null
  /** Unit of measurement (e.g. g, ml, katori, chamcha, paav). */
  unit?: string | null
  /** Whether the ingredient is optional for the dish. */
  optional?: boolean
  /** Group heading for multi-part recipes (e.g. "For Tadka"). */
  group?: string | null
  /** Preparation notes (e.g. "finely chopped", "soaked overnight"). */
  notes?: string | null
}

// Represent an ordered cooking step.
// Track step numbers explicitly to guarantee sequential rendering regardless of array ordering.
export interface Step {
  /** 1-based sequential step number. */
  step_number: number
  /** Instruction text describing this cooking action. */
  instruction: string
  /** Estimated time in minutes for this step. */
  time_minutes?: number | null
}

// Model macronutrient breakdown per serving.
// Values are optional because some sources omit nutritional data.
export interface NutritionInfo {
  /** Total energy in kilocalories. */
  calories?: number | null
  /** Protein in grams. */
  protein?: number | null
  /** Carbohydrates in grams. */
  carbs?: number | null
  /** Total fat in grams. */
  fat?: number | null
  /** Dietary fiber in grams. */
  fiber?: number | null
}

// Store full recipe record with metadata and media.
// Support both _id and id properties to handle MongoDB ObjectId and Supabase UUID interchangeably.
export interface Recipe {
  /** MongoDB primary key identifier. */
  _id?: string
  /** Normalized or Supabase primary key identifier. */
  id?: string
  /** Recipe title. */
  title: string
  /** Optional summary or background description. */
  description?: string | null
  /** List of ingredients with quantities and units. */
  ingredients: IngredientItem[]
  /** Step-by-step preparation instructions in order. */
  steps: Step[]
  /** Indian or international region tag (e.g. "North India", "South India"). */
  region?: string | null
  /** Dietary category (e.g. "veg", "non_veg", "vegan", "jain"). */
  cuisine_type?: string | null
  /** Skill level required (e.g. "easy", "medium", "hard"). */
  difficulty?: string | null
  /** Preparation time in minutes before active cooking starts. */
  prep_time_minutes?: number | null
  /** Active cooking time in minutes. */
  cook_time_minutes?: number | null
  /** Number of standard portions this recipe yields. */
  servings?: number | null
  /** Origin website or video URL. */
  source_url?: string | null
  /** Name of the author or publication source. */
  source_name?: string | null
  /** Hero image URL or data URI. */
  image_url?: string | null
  /** Direct video playback URL for YouTube or reel sources. */
  video_url?: string | null
  /** Search and filtering tags. */
  tags?: string[]
  /** Per-serving nutritional macronutrients. */
  nutrition?: NutritionInfo | null
  /** ISO-8601 creation timestamp. */
  created_at?: string
  /** ISO-8601 last modification timestamp. */
  updated_at?: string
}

// Track active inventory on hand in the kitchen pantry.
// Include days_to_expiry for FEFO (First-Expire-First-Out) sorting and color-coded alert badges.
export interface InventoryItem {
  /** Primary identifier. */
  id: string
  /** Item name. */
  name: string
  /** Current available quantity. */
  quantity: number
  /** Unit of measurement. */
  unit: string
  /** Physical kitchen storage location (e.g. "fridge", "pantry", "spice_box"). */
  location: string
  /** ISO-8601 date string for item expiration. */
  expiry_date?: string | null
  /** ISO-8601 date string when item was stocked. */
  created_at?: string
  /** Calculated days until expiration. Negative numbers indicate expired stock. */
  days_to_expiry?: number | null
}

// Payload for adding a new pantry item.
// Keep separated from InventoryItem because ID and timestamps are assigned by the backend.
export interface InventoryCreate {
  /** Item name. */
  name: string
  /** Quantity stocked. */
  quantity: number
  /** Unit of measurement. */
  unit: string
  /** Storage location in the kitchen. */
  location: string
  /** Optional expiry date. */
  expiry_date?: string | null
}

// Represent system credentials and provider connection status.
// Return masked strings (e.g. "AIzaSy...****") to prevent leaking secrets to browser devtools.
export interface SettingsStatus {
  /** Active storage backend ("supabase", "mongodb", or "memory"). */
  database_backend: string
  /** Whether Supabase URL and key are configured. */
  supabase_configured: boolean
  /** Active Supabase project URL. */
  supabase_url?: string | null
  /** Partially masked Supabase key. */
  supabase_key_masked?: string | null
  /** Whether Google Gemini BYOK API key is configured. */
  gemini_configured: boolean
  /** Partially masked Gemini API key. */
  gemini_api_key_masked?: string | null
  /** Active Gemini model identifier (e.g. "gemini-2.5-flash"). */
  gemini_model: string
  /** Whether Anthropic API key is configured. */
  anthropic_configured: boolean
  /** Partially masked Anthropic API key. */
  anthropic_api_key_masked?: string | null
  /** Active Claude model identifier for extraction. */
  anthropic_model_extract: string
  /** Whether OpenAI API key is configured. */
  openai_configured: boolean
  /** Partially masked OpenAI API key. */
  openai_api_key_masked?: string | null
  /** Whether Voyage AI embedding API key is configured. */
  voyage_configured: boolean
  /** Partially masked Voyage API key. */
  voyage_api_key_masked?: string | null
  /** Currently active model provider name for user display. */
  active_llm_provider: string
  /** Whether a persistent .env file is present on the server filesystem. */
  env_file_exists: boolean
}

// Payload for updating server configuration and API keys.
// All fields are optional to allow partial updates without overwriting existing credentials.
export interface UpdateSettingsPayload {
  /** Supabase project URL. */
  supabase_url?: string
  /** Supabase service or anon key. */
  supabase_key?: string
  /** Google Gemini API key. */
  gemini_api_key?: string
  /** Google Gemini model identifier. */
  gemini_model?: string
  /** Anthropic Claude API key. */
  anthropic_api_key?: string
  /** OpenAI API key. */
  openai_api_key?: string
  /** Voyage AI embedding key. */
  voyage_api_key?: string
}
