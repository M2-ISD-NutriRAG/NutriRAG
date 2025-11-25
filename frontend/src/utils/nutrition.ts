/**
 * Display utilities for nutritional data
 * !!! These functions are ONLY for display in the frontend
 * All business calculations are done in the backend
 */

/**
 * Formats a nutritional value for display
 * @param value Value to format
 * @param decimals Number of decimals (default: 1)
 * @returns Formatted value as string
 */
export function formatNutritionValue(
  value: number,
  decimals: number = 1,
): string {
  return value.toFixed(decimals);
}

/**
 * Returns the appropriate color for a nutritional value
 * Used for UI (badges, indicators)
 * @param value Nutritional value
 * @param type Nutrient type
 * @returns Color code: 'green' (good), 'orange' (medium), 'red' (bad)
 */
export function getNutritionColor(
  value: number,
  type: "protein" | "carbs" | "fat" | "calories" | "fiber" | "sodium",
): "green" | "orange" | "red" {
  switch (type) {
    case "protein":
      return value >= 30 ? "green" : value >= 15 ? "orange" : "red";
    case "fiber":
      return value >= 10 ? "green" : value >= 5 ? "orange" : "red";
    case "calories":
      return value <= 400 ? "green" : value <= 600 ? "orange" : "red";
    case "carbs":
      return value <= 50 ? "green" : value <= 100 ? "orange" : "red";
    case "fat":
      return value <= 20 ? "green" : value <= 40 ? "orange" : "red";
    case "sodium":
      return value <= 500 ? "green" : value <= 1000 ? "orange" : "red";
    default:
      return "orange";
  }
}

/**
 * Returns the English name of a nutrient
 */
export function getNutrientName(type: string): string {
  const names: Record<string, string> = {
    calories: "Calories",
    protein: "Protein",
    protein_g: "Protein",
    carbs: "Carbs",
    carbs_g: "Carbs",
    fat: "Fat",
    fat_g: "Fat",
    fiber: "Fiber",
    fiber_g: "Fiber",
    sodium: "Sodium",
    sodium_mg: "Sodium",
    sugar: "Sugar",
    sugar_g: "Sugar",
    saturated_fat: "Saturated Fat",
    saturated_fat_g: "Saturated Fat",
  };
  return names[type] || type;
}

/**
 * Formats the unit of a nutrient
 */
export function getNutrientUnit(type: string): string {
  if (type.includes("_mg")) return "mg";
  if (type.includes("_g")) return "g";
  if (type === "calories") return "kcal";
  return "";
}
