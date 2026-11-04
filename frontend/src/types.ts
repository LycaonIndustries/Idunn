export interface IngredientItem {
  name: string
  quantity?: number | null
  unit?: string | null
  optional?: boolean
  group?: string | null
  notes?: string | null
}

export interface Step {
  step_number: number
  instruction: string
  time_minutes?: number | null
}

export interface NutritionInfo {
  calories?: number | null
  protein?: number | null
  carbs?: number | null
  fat?: number | null
  fiber?: number | null
}

export interface Recipe {
  _id?: string
  id?: string
  title: string
  description?: string | null
  ingredients: IngredientItem[]
  steps: Step[]
  region?: string | null
  cuisine_type?: string | null
  difficulty?: string | null
  prep_time_minutes?: number | null
  cook_time_minutes?: number | null
  servings?: number | null
  source_url?: string | null
  source_name?: string | null
  image_url?: string | null
  video_url?: string | null
  tags?: string[]
  nutrition?: NutritionInfo | null
  created_at?: string
  updated_at?: string
}

export interface InventoryItem {
  id: string
  name: string
  quantity: number
  unit: string
  location: string
  expiry_date?: string | null
  created_at?: string
  days_to_expiry?: number | null
}

export interface InventoryCreate {
  name: string
  quantity: number
  unit: string
  location: string
  expiry_date?: string | null
}

export interface SettingsStatus {
  gemini_configured: boolean
  gemini_api_key_masked?: string | null
  gemini_model: string
  anthropic_configured: boolean
  anthropic_api_key_masked?: string | null
  anthropic_model_extract: string
  openai_configured: boolean
  openai_api_key_masked?: string | null
  voyage_configured: boolean
  voyage_api_key_masked?: string | null
  active_llm_provider: string
  env_file_exists: boolean
}

export interface UpdateSettingsPayload {
  gemini_api_key?: string
  gemini_model?: string
  anthropic_api_key?: string
  openai_api_key?: string
  voyage_api_key?: string
}
