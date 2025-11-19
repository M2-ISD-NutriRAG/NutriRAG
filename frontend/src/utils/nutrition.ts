/**
 * Utilitaires d'affichage pour les données nutritionnelles
 * ⚠️ Ces fonctions sont UNIQUEMENT pour l'affichage dans le frontend
 * Tous les calculs métier sont faits dans le backend
 */

/**
 * Formate une valeur nutritionnelle pour l'affichage
 * @param value Valeur à formater
 * @param decimals Nombre de décimales (défaut: 1)
 * @returns Valeur formatée en string
 */
export function formatNutritionValue(value: number, decimals: number = 1): string {
  return value.toFixed(decimals)
}

/**
 * Retourne la couleur appropriée pour une valeur nutritionnelle
 * Utilisé pour l'UI (badges, indicateurs)
 * @param value Valeur nutritionnelle
 * @param type Type de nutriment
 * @returns Code couleur: 'green' (bon), 'orange' (moyen), 'red' (mauvais)
 */
export function getNutritionColor(
  value: number,
  type: 'protein' | 'carbs' | 'fat' | 'calories' | 'fiber' | 'sodium'
): 'green' | 'orange' | 'red' {
  switch (type) {
    case 'protein':
      return value >= 30 ? 'green' : value >= 15 ? 'orange' : 'red'
    case 'fiber':
      return value >= 10 ? 'green' : value >= 5 ? 'orange' : 'red'
    case 'calories':
      return value <= 400 ? 'green' : value <= 600 ? 'orange' : 'red'
    case 'carbs':
      return value <= 50 ? 'green' : value <= 100 ? 'orange' : 'red'
    case 'fat':
      return value <= 20 ? 'green' : value <= 40 ? 'orange' : 'red'
    case 'sodium':
      return value <= 500 ? 'green' : value <= 1000 ? 'orange' : 'red'
    default:
      return 'orange'
  }
}

/**
 * Retourne le nom en français d'un nutriment
 */
export function getNutrientName(type: string): string {
  const names: Record<string, string> = {
    calories: 'Calories',
    protein: 'Protéines',
    protein_g: 'Protéines',
    carbs: 'Glucides',
    carbs_g: 'Glucides',
    fat: 'Lipides',
    fat_g: 'Lipides',
    fiber: 'Fibres',
    fiber_g: 'Fibres',
    sodium: 'Sodium',
    sodium_mg: 'Sodium',
    sugar: 'Sucres',
    sugar_g: 'Sucres',
    saturated_fat: 'Graisses saturées',
    saturated_fat_g: 'Graisses saturées',
  }
  return names[type] || type
}

/**
 * Formate l'unité d'un nutriment
 */
export function getNutrientUnit(type: string): string {
  if (type.includes('_mg')) return 'mg'
  if (type.includes('_g')) return 'g'
  if (type === 'calories') return 'kcal'
  return ''
}

