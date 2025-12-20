from typing import Dict, Any
from backend.app.models.recipe import NutritionDetailed

ingredients_amounts: Dict[str, float]
nutrition_table: Dict[str, Dict[str, float]]

def compute_nutrition_for_ingredient(
    grams: float,
    nutrition_per_100g: Dict[str, Any],
) -> NutritionDetailed:
    """
    Compute nutrition for a given *amount* of an ingredient.
    
    Parameters
    ----------
    grams : amount used for ingredient
    nutrition_per_100g : dict
        Nutrients per 100 g for this ingredient from  DB:
        {
            "ENERGY_KCAL": 717.0,
            "PROTEIN_G": 0.85,
            "FAT_G": 81.11,
            "SATURATED_FATS_G": 51.37,
            "CARB_G": 0.06,
            "FIBER_G": 0.0,
            "SUGAR_G": 0.06,
            "SODIUM_MG": 11.0,
            "CALCIUM_MG": ...,
            ...
        }
    
    Returns
    -------
    NutritionDetailed
        Nutrition **for that amount** of this ingredient (not per 100 g).
    """
    factor = grams / 100.0 

    def val(key: str) -> float:
        v = nutrition_per_100g.get(key)
        if v is None:
            return 0.0
        return float(v) * factor

    return NutritionDetailed(
        calories=val("ENERGY_KCAL"),
        protein_g=val("PROTEIN_G"),
        fat_g=val("FAT_G"),
        saturated_fat_g=val("SATURATED_FATS_G"),
        carbs_g=val("CARB_G"),
        fiber_g=val("FIBER_G"),
        sugar_g=val("SUGAR_G"),
        sodium_mg=val("SODIUM_MG"),

        calcium_mg=val("CALCIUM_MG"),
        iron_mg=val("IRON_MG"),
        magnesium_mg=val("MAGNESIUM_MG"),
        potassium_mg=val("POTASSIUM_MG"),
        vitamin_c_mg=val("VITC_MG"),
    )

def compute_recipe_nutrition_totals(
    ingredients_amounts: Dict[str, float],
    nutrition_table: Dict[str, Dict[str, Any]],
) -> NutritionDetailed:
    """
    Compute recipe nutrition information for all ingredients

    Parameters
    ----------
    ingredients_amounts : recipe ingredients quantity dict
    nutrition_table : recipe ingredients nutrition dict
    Returns
    -------
    NutritionDetailed
        Total nutrients for the  recipe
    """
    recipe_nutrition = NutritionDetailed(
        calories=0.0,
        protein_g=0.0,
        fat_g=0.0,
        saturated_fat_g=0.0,
        carbs_g=0.0,
        fiber_g=0.0,
        sugar_g=0.0,
        sodium_mg=0.0,
        calcium_mg=0.0,
        iron_mg=0.0,
        magnesium_mg=0.0,
        potassium_mg=0.0,
        vitamin_c_mg=0.0,
    )

    for name, grams in ingredients_amounts.items():
        nutr_100g = nutrition_table.get(name)
        if nutr_100g is None:
            continue

        ing_nut = compute_nutrition_for_ingredient(grams, nutr_100g)

        recipe_nutrition.calories += ing_nut.calories
        recipe_nutrition.protein_g += ing_nut.protein_g
        recipe_nutrition.fat_g += ing_nut.fat_g
        recipe_nutrition.saturated_fat_g += ing_nut.saturated_fat_g
        recipe_nutrition.carbs_g += ing_nut.carbs_g
        recipe_nutrition.fiber_g += ing_nut.fiber_g
        recipe_nutrition.sugar_g += ing_nut.sugar_g
        recipe_nutrition.sodium_mg += ing_nut.sodium_mg

        recipe_nutrition.calcium_mg += ing_nut.calcium_mg
        recipe_nutrition.iron_mg += ing_nut.iron_mg
        recipe_nutrition.magnesium_mg += ing_nut.magnesium_mg
        recipe_nutrition.potassium_mg += ing_nut.potassium_mg
        recipe_nutrition.vitamin_c_mg += ing_nut.vitamin_c_mg

    return recipe_nutrition

def compute_benefit_score(protein_g: float, fiber_g: float) -> float:
    """
    Compute the benefit score of a recipe based on total protein and fiber.
    Returns a value in [0, 1].
    """
    protein_ref = 50.0  
    fiber_ref   = 30.0

    s_protein = min(protein_g / protein_ref, 1.0)
    s_fiber   = min((fiber_g or 0.0) / fiber_ref, 1.0)

    benefit_score = (s_protein + s_fiber) / 2.0

    return benefit_score

def compute_risk_score(
    sugar_g: float,
    saturated_fat_g: float,
    sodium_mg: float,
    alpha_sugar: float = 1.2,
    alpha_satfat: float = 1.0,
    alpha_sodium: float = 1.5,
) -> float:
    """
    Compute risk score where exceeding nutrient limits creates negative scores proportional to how badly limits are exceeded.
    Returns float between -inf and 1.0
    """

    Sugar_limit = 50.0     
    SatFat_limit = 20.0   
    Sodium_limit = 2000.0

    def subscore(x, L, alpha):
        x = max(x, 0.0)
        if x <= L:
            return 1.0 - (x / L)
        else:
            return -alpha * ((x / L) - 1.0)

    h_sugar   = subscore(sugar_g, Sugar_limit, alpha_sugar)
    h_satfat  = subscore(saturated_fat_g, SatFat_limit, alpha_satfat)
    h_sodium  = subscore(sodium_mg, Sodium_limit, alpha_sodium)

    risk_control_score = (h_sugar + h_satfat + h_sodium) / 3.0
    return risk_control_score

def compute_micronutrient_density_score(
    calcium_mg: float,
    iron_mg: float,
    magnesium_mg: float,
    potassium_mg: float,
    vitamin_c_mg: float,
) -> float:
    """
    Compute a micronutrient density score in [0, 1] based on totals for the recipe.
    """

    Calcium_ref   = 1000.0
    Iron_ref      = 18.0
    Magnesium_ref = 350.0
    Potassium_ref = 3500.0
    VitC_ref      = 90.0

    m_ca = min(max(calcium_mg, 0.0)   / Calcium_ref,   1.0)
    m_fe = min(max(iron_mg, 0.0)      / Iron_ref,      1.0)
    m_mg = min(max(magnesium_mg, 0.0) / Magnesium_ref, 1.0)
    m_k  = min(max(potassium_mg, 0.0) / Potassium_ref, 1.0)
    m_c  = min(max(vitamin_c_mg, 0.0) / VitC_ref,      1.0)

    micronutrient_score = (m_ca + m_fe + m_mg + m_k + m_c) / 5.0

    return micronutrient_score

def compute_rhi(nutrition: NutritionDetailed) -> float:
    """
    Compute the Recipe Health Index (RHI) on [0, 100] for a whole recipe.
    Uses:
      - benefit score (protein + fiber, vs daily references)
      - risk score (sugar, saturated fat, sodium vs daily limits, with penalties above limits)
      - micronutrient density score (Ca, Fe, Mg, K, Vit C vs daily references)

    RHI = max(0, 0.4 * risk + 0.4 * benefit + 0.2 * micro) * 100
    """

    benefit = compute_benefit_score(protein_g=nutrition.protein_g, fiber_g=nutrition.fiber_g)
    risk = compute_risk_score(
        sugar_g=nutrition.sugar_g,
        saturated_fat_g=nutrition.sat_fat_g,
        sodium_mg=nutrition.sodium_mg,
    )
    micro = compute_micronutrient_density_score(
        calcium_mg=nutrition.calcium_mg,
        iron_mg=nutrition.iron_mg,
        magnesium_mg=nutrition.magnesium_mg,
        potassium_mg=nutrition.potassium_mg,
        vitamin_c_mg=nutrition.vitamin_c_mg,
    )

    rhi_raw = 0.4 * risk + 0.4 * benefit + 0.2 * micro

    rhi_0_1 = max(0.0, min(1.0, rhi_raw))
    rhi = rhi_0_1 * 100.0

    return rhi
