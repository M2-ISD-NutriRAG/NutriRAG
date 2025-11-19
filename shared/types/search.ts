/**
 * Shared type definitions for Search functionality
 */

export interface SearchFilters {
  protein_min?: number
  protein_max?: number
  carbs_min?: number
  carbs_max?: number
  calories_min?: number
  calories_max?: number
  fat_max?: number
  fiber_min?: number
  sodium_max?: number
  
  // Tags filters
  tags_include?: string[]
  tags_exclude?: string[]
  
  // Score filters
  score_health_min?: number
  rating_min?: number
}

export interface SearchRequest {
  query: string
  filters?: SearchFilters
  limit?: number
}

export interface SearchResult {
  id: number
  name: string
  description?: string
  similarity: number
  nutrition?: Record<string, number>
  score_health?: number
  rating_avg?: number
  tags: string[]
}

export interface SearchResponse {
  results: SearchResult[]
  query: string
  total_found: number
  execution_time_ms: number
}

