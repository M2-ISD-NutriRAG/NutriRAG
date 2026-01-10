-- ============================================================================
-- PARTIE 1 : ENRICHISSEMENT DES INGRÉDIENTS
-- ============================================================================

-- Créer la table enrichie à partir des données avec clusters
CREATE OR REPLACE TABLE {database}.{enriched_schema}.INGREDIENTS AS
SELECT *
FROM {database}.{analytics_schema}.INGREDIENTS_WITH_CLUSTERS;

-- Ajouter la colonne score santé
ALTER TABLE {database}.{enriched_schema}.INGREDIENTS 
ADD COLUMN IF NOT EXISTS SCORE_SANTE FLOAT;

-- Fonction de calcul du score santé (0-100)
UPDATE {database}.{enriched_schema}.INGREDIENTS
SET SCORE_SANTE = GREATEST(0, (
    -- 40% : Bénéfices nutritionnels (protéines, fibres)
    0.4 * (LEAST(PROTEIN_G / 50, 1) + LEAST(FIBER_G / 30, 1)) / 2
    
    -- 40% : Risques nutritionnels (sucres, graisses saturées, sodium)
    + 0.4 * (
        CASE WHEN SUGAR_G <= 50 
            THEN 1 - (SUGAR_G / 50)
            ELSE -1.2 * ((SUGAR_G / 50) - 1)
        END
        + CASE WHEN SATURATED_FATS_G <= 20 
            THEN 1 - (SATURATED_FATS_G / 20)
            ELSE -1.0 * ((SATURATED_FATS_G / 20) - 1)
        END
        + CASE WHEN SODIUM_MG <= 2000 
            THEN 1 - (SODIUM_MG / 2000)
            ELSE -1.5 * ((SODIUM_MG / 2000) - 1)
        END
    ) / 3
    
    -- 20% : Micronutriments (calcium, fer, potassium, vitamine C, magnésium)
    + 0.2 * (
        LEAST(CALCIUM_MG / 1000, 1)
        + LEAST(IRON_MG / 18, 1)
        + LEAST(POTASSIUM_MG / 3500, 1)
        + LEAST(VITC_MG / 90, 1)
        + LEAST(MAGNESIUM_MG / 350, 1)
    ) / 5
) * 100);


-- ============================================================================
-- PARTIE 2 : ENRICHISSEMENT DES RECETTES
-- ============================================================================

-- Créer la table avec colonnes nutritionnelles
CREATE OR REPLACE TABLE {database}.{enriched_schema}.RECIPES_SAMPLE_50K AS
SELECT 
    *,
    CAST(0 AS FLOAT) AS score_sante,
    CAST(0 AS FLOAT) AS energy_kcal_100g,
    CAST(0 AS FLOAT) AS protein_g_100g,
    CAST(0 AS FLOAT) AS saturated_fats_g_100g,
    CAST(0 AS FLOAT) AS fat_g_100g,
    CAST(0 AS FLOAT) AS carb_g_100g,
    CAST(0 AS FLOAT) AS fiber_g_100g,
    CAST(0 AS FLOAT) AS sugar_g_100g,
    CAST(0 AS FLOAT) AS sodium_mg_100g,
    CAST(0 AS FLOAT) AS calcium_mg_100g,
    CAST(0 AS FLOAT) AS iron_mg_100g,
    CAST(0 AS FLOAT) AS potassium_mg_100g,
    CAST(0 AS FLOAT) AS vitc_mg_100g,
    CAST(0 AS FLOAT) AS magnesium_mg_100g
FROM {database}.{cleaned_schema}.RECIPES_SAMPLE_50K;

-- Calculer les valeurs nutritionnelles pour 100g
MERGE INTO {database}.{enriched_schema}.RECIPES_SAMPLE_50K AS target
USING (
    WITH 
    -- Étape 1 : Calculer le poids total de chaque recette
    recipe_weights AS (
        SELECT 
            id,
            serving_size * servings AS total_weight
        FROM {database}.{cleaned_schema}.RECIPES_SAMPLE_50K
    ),
    
    -- Étape 2 : Analyser les quantités d'ingrédients connues vs inconnues
    ingredient_stats AS (
        SELECT 
            iq.id AS recipe_id,
            rw.total_weight,
            SUM(COALESCE(iq.qty_g, 0)) AS known_weight,
            COUNT(CASE WHEN iq.qty_g IS NULL THEN 1 END) AS unknown_count
        FROM {database}.{cleaned_schema}.INGREDIENTS_QUANTITY iq
        INNER JOIN recipe_weights rw ON iq.id = rw.id
        GROUP BY iq.id, rw.total_weight
    ),
    
    -- Étape 3 : Imputer les quantités manquantes
    ingredients_with_qty AS (
        SELECT 
            iq.id AS recipe_id,
            iq.ingredients,
            COALESCE(
                iq.qty_g,
                CASE 
                    WHEN ist.unknown_count > 0 
                    THEN GREATEST(ist.total_weight - ist.known_weight, 0) / ist.unknown_count * 0.5
                    ELSE 0
                END
            ) AS qty_g
        FROM {database}.{cleaned_schema}.INGREDIENTS_QUANTITY iq
        INNER JOIN ingredient_stats ist ON iq.id = ist.recipe_id
    ),
    
    -- Étape 4 : Sélectionner le meilleur match USDA (score_sante max)
    best_ingredient_matches AS (
        SELECT 
            im.recipe_id,
            im.ingredient_from_recipe_name,
            ing.energy_kcal,
            ing.protein_g,
            ing.saturated_fats_g,
            ing.fat_g,
            ing.carb_g,
            ing.fiber_g,
            ing.sugar_g,
            ing.sodium_mg,
            ing.calcium_mg,
            ing.iron_mg,
            ing.potassium_mg,
            ing.vitc_mg,
            ing.magnesium_mg,
            ROW_NUMBER() OVER (
                PARTITION BY im.recipe_id, im.ingredient_from_recipe_name 
                ORDER BY ing.score_sante DESC NULLS LAST
            ) AS rn
        FROM {database}.{cleaned_schema}.INGREDIENTS_MATCHING im
        LEFT JOIN {database}.{enriched_schema}.INGREDIENTS ing ON im.ingredient_id = ing.ndb_no
    ),
    
    -- Étape 5 : Calculer les totaux nutritionnels par recette
    recipe_nutrition_totals AS (
        SELECT 
            iwq.recipe_id,
            ist.total_weight,
            ist.known_weight,
            SUM(COALESCE(bim.energy_kcal, 0) * iwq.qty_g / 100) AS energy_kcal_sum,
            SUM(COALESCE(bim.protein_g, 0) * iwq.qty_g / 100) AS protein_g_sum,
            SUM(COALESCE(bim.saturated_fats_g, 0) * iwq.qty_g / 100) AS saturated_fats_g_sum,
            SUM(COALESCE(bim.fat_g, 0) * iwq.qty_g / 100) AS fat_g_sum,
            SUM(COALESCE(bim.carb_g, 0) * iwq.qty_g / 100) AS carb_g_sum,
            SUM(COALESCE(bim.fiber_g, 0) * iwq.qty_g / 100) AS fiber_g_sum,
            SUM(COALESCE(bim.sugar_g, 0) * iwq.qty_g / 100) AS sugar_g_sum,
            SUM(COALESCE(bim.sodium_mg, 0) * iwq.qty_g / 100) AS sodium_mg_sum,
            SUM(COALESCE(bim.calcium_mg, 0) * iwq.qty_g / 100) AS calcium_mg_sum,
            SUM(COALESCE(bim.iron_mg, 0) * iwq.qty_g / 100) AS iron_mg_sum,
            SUM(COALESCE(bim.potassium_mg, 0) * iwq.qty_g / 100) AS potassium_mg_sum,
            SUM(COALESCE(bim.vitc_mg, 0) * iwq.qty_g / 100) AS vitc_mg_sum,
            SUM(COALESCE(bim.magnesium_mg, 0) * iwq.qty_g / 100) AS magnesium_mg_sum
        FROM ingredients_with_qty iwq
        INNER JOIN ingredient_stats ist ON iwq.recipe_id = ist.recipe_id
        LEFT JOIN best_ingredient_matches bim 
            ON iwq.recipe_id = bim.recipe_id 
            AND iwq.ingredients = bim.ingredient_from_recipe_name
            AND bim.rn = 1
        GROUP BY iwq.recipe_id, ist.total_weight, ist.known_weight
    )
    
    -- Étape 6 : Convertir en valeurs pour 100g
    SELECT 
        recipe_id AS id,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN energy_kcal_sum / GREATEST(total_weight, known_weight) * 100 
        END AS energy_kcal_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN protein_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS protein_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN saturated_fats_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS saturated_fats_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN fat_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS fat_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN carb_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS carb_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN fiber_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS fiber_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN sugar_g_sum / GREATEST(total_weight, known_weight) * 100 
        END AS sugar_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN sodium_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS sodium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN calcium_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS calcium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN iron_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS iron_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN potassium_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS potassium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN vitc_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS vitc_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN magnesium_mg_sum / GREATEST(total_weight, known_weight) * 100 
        END AS magnesium_mg_100g
    FROM recipe_nutrition_totals
) AS source
ON target.id = source.id
WHEN MATCHED THEN UPDATE SET
    target.energy_kcal_100g = source.energy_kcal_100g,
    target.protein_g_100g = source.protein_g_100g,
    target.saturated_fats_g_100g = source.saturated_fats_g_100g,
    target.fat_g_100g = source.fat_g_100g,
    target.carb_g_100g = source.carb_g_100g,
    target.fiber_g_100g = source.fiber_g_100g,
    target.sugar_g_100g = source.sugar_g_100g,
    target.sodium_mg_100g = source.sodium_mg_100g,
    target.calcium_mg_100g = source.calcium_mg_100g,
    target.iron_mg_100g = source.iron_mg_100g,
    target.potassium_mg_100g = source.potassium_mg_100g,
    target.vitc_mg_100g = source.vitc_mg_100g,
    target.magnesium_mg_100g = source.magnesium_mg_100g;

-- Calculer le score santé pour chaque recette
UPDATE {database}.{enriched_schema}.RECIPES_SAMPLE_50K
SET SCORE_SANTE = CASE 
    WHEN ENERGY_KCAL_100G = 0 THEN 0
    ELSE GREATEST(0, (
        -- 40% : Bénéfices nutritionnels
        0.4 * (
            LEAST(COALESCE(PROTEIN_G_100G, 0) / 50, 1)
            + LEAST(COALESCE(FIBER_G_100G, 0) / 30, 1)
        ) / 2
        
        -- 40% : Risques nutritionnels
        + 0.4 * (
            CASE WHEN COALESCE(SUGAR_G_100G, 0) <= 50
                THEN 1 - (COALESCE(SUGAR_G_100G, 0) / 50)
                ELSE -1.2 * ((COALESCE(SUGAR_G_100G, 0) / 50) - 1)
            END
            + CASE WHEN COALESCE(SATURATED_FATS_G_100G, 0) <= 20
                THEN 1 - (COALESCE(SATURATED_FATS_G_100G, 0) / 20)
                ELSE -1.0 * ((COALESCE(SATURATED_FATS_G_100G, 0) / 20) - 1)
            END
            + CASE WHEN COALESCE(SODIUM_MG_100G, 0) <= 2000
                THEN 1 - (COALESCE(SODIUM_MG_100G, 0) / 2000)
                ELSE -1.5 * ((COALESCE(SODIUM_MG_100G, 0) / 2000) - 1)
            END
        ) / 3
        
        -- 20% : Micronutriments
        + 0.2 * (
            LEAST(COALESCE(CALCIUM_MG_100G, 0) / 1000, 1)
            + LEAST(COALESCE(IRON_MG_100G, 0) / 18, 1)
            + LEAST(COALESCE(POTASSIUM_MG_100G, 0) / 3500, 1)
            + LEAST(COALESCE(VITC_MG_100G, 0) / 90, 1)
            + LEAST(COALESCE(MAGNESIUM_MG_100G, 0) / 350, 1)
        ) / 5
    ) * 100)
END;