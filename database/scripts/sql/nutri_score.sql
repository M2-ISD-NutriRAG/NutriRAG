ALTER TABLE NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS 
ADD COLUMN IF NOT EXISTS SCORE_SANTE FLOAT;


UPDATE NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS
SET MAGNESIUM_MG = 0
WHERE NDB_NO = 'P042';

UPDATE NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS
SET SCORE_SANTE = GREATEST(0,
    (
        -- 40% BENEFICES
        0.4 * (
            (
                LEAST(PROTEIN_G / 50, 1)
                + LEAST(FIBER_G / 30, 1)
            ) / 2
        )
        +
        -- 40% RISQUES
        0.4 * (
            (
                -- SUGAR_G pénalisé
                CASE WHEN SUGAR_G <= 50
                     THEN 1 - (SUGAR_G / 50)
                     ELSE -1.2 * ((SUGAR_G / 50) - 1)
                END
                +
                -- SATURATED_FATS_G pénalisé
                CASE WHEN SATURATED_FATS_G <= 20
                     THEN 1 - (SATURATED_FATS_G / 20)
                     ELSE -1.0 * ((SATURATED_FATS_G / 20) - 1)
                END
                +
                -- SODIUM_MG pénalisé
                CASE WHEN SODIUM_MG <= 2000
                     THEN 1 - (SODIUM_MG / 2000)
                     ELSE -1.5 * ((SODIUM_MG / 2000) - 1)
                END
            ) / 3
        )
        +
        -- 20% MICRO-NUTRIENTS
        0.2 * (
            (
                LEAST(CALCIUM_MG / 1000, 1)
                + LEAST(IRON_MG / 18, 1)
                + LEAST(POTASSIUM_MG / 3500, 1)
                + LEAST(VITC_MG / 90, 1)
                + LEAST(MAGNESIUM_MG / 350, 1)
            ) / 5
        )
    ) * 100
);


MERGE INTO NUTRIRAG_PROJECT.ENRICHED.RECIPES_SAMPLE_50K AS target
USING (
    WITH recipe_base AS (
        -- Récupérer le poids total de chaque recette
        SELECT 
            id,
            serving_size * servings AS total_weight
        FROM NUTRIRAG_PROJECT.CLEANED.RECIPES_SAMPLE_50K
    ),
    
    ingredients_with_qty AS (
        -- Charger les ingrédients avec leurs quantités
        SELECT 
            iq.id AS recipe_id,
            iq.ingredient,
            iq.qty_g,
            rb.total_weight
        FROM NUTRIRAG_PROJECT.RAW.INGREDIENTS_QUANTITY iq
        INNER JOIN recipe_base rb ON iq.id = rb.id
    ),
    
    qty_stats AS (
        -- Calculer les statistiques de quantités par recette
        SELECT 
            recipe_id,
            total_weight,
            SUM(COALESCE(qty_g, 0)) AS known_weight,
            COUNT(CASE WHEN qty_g IS NULL THEN 1 END) AS unknown_count,
            COUNT(*) AS total_count
        FROM ingredients_with_qty
        GROUP BY recipe_id, total_weight
    ),
    
    ingredients_filled AS (
        -- Remplir les quantités manquantes
        SELECT 
            iwq.recipe_id,
            iwq.ingredient,
            iwq.total_weight,
            qs.known_weight,
            COALESCE(
                iwq.qty_g,
                CASE 
                    WHEN qs.unknown_count > 0 
                    THEN GREATEST(qs.total_weight - qs.known_weight, 0) / qs.unknown_count * 0.5
                    ELSE 0
                END
            ) AS qty_g_filled
        FROM ingredients_with_qty iwq
        INNER JOIN qty_stats qs ON iwq.recipe_id = qs.recipe_id
    ),
    
    best_matches AS (
        -- Sélectionner le meilleur match USDA pour chaque ingrédient (score_sante max)
        SELECT 
            im.recipe_id,
            im.ingredient_from_recipe_name AS ingredient,
            im.ingredient_id,
            ci.energy_kcal,
            ci.protein_g,
            ci.saturated_fats_g,
            ci.fat_g,
            ci.carb_g,
            ci.fiber_g,
            ci.sugar_g,
            ci.sodium_mg,
            ci.calcium_mg,
            ci.iron_mg,
            ci.potassium_mg,
            ci.vitc_mg,
            ci.magnesium_mg,
            ROW_NUMBER() OVER (
                PARTITION BY im.recipe_id, im.ingredient_from_recipe_name 
                ORDER BY ci.score_sante DESC NULLS LAST
            ) AS rn
        FROM NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING im
        LEFT JOIN NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS ci 
            ON im.ingredient_id = ci.ndb_no
    ),
    
    ingredients_with_nutrition AS (
        -- Joindre quantités et données nutritionnelles
        SELECT 
            if_data.recipe_id,
            if_data.total_weight,
            if_data.known_weight,
            if_data.qty_g_filled,
            COALESCE(bm.energy_kcal, 0) * (if_data.qty_g_filled / 100) AS energy_kcal_total,
            COALESCE(bm.protein_g, 0) * (if_data.qty_g_filled / 100) AS protein_g_total,
            COALESCE(bm.saturated_fats_g, 0) * (if_data.qty_g_filled / 100) AS saturated_fats_g_total,
            COALESCE(bm.fat_g, 0) * (if_data.qty_g_filled / 100) AS fat_g_total,
            COALESCE(bm.carb_g, 0) * (if_data.qty_g_filled / 100) AS carb_g_total,
            COALESCE(bm.fiber_g, 0) * (if_data.qty_g_filled / 100) AS fiber_g_total,
            COALESCE(bm.sugar_g, 0) * (if_data.qty_g_filled / 100) AS sugar_g_total,
            COALESCE(bm.sodium_mg, 0) * (if_data.qty_g_filled / 100) AS sodium_mg_total,
            COALESCE(bm.calcium_mg, 0) * (if_data.qty_g_filled / 100) AS calcium_mg_total,
            COALESCE(bm.iron_mg, 0) * (if_data.qty_g_filled / 100) AS iron_mg_total,
            COALESCE(bm.potassium_mg, 0) * (if_data.qty_g_filled / 100) AS potassium_mg_total,
            COALESCE(bm.vitc_mg, 0) * (if_data.qty_g_filled / 100) AS vitc_mg_total,
            COALESCE(bm.magnesium_mg, 0) * (if_data.qty_g_filled / 100) AS magnesium_mg_total
        FROM ingredients_filled if_data
        LEFT JOIN best_matches bm 
            ON if_data.recipe_id = bm.recipe_id 
            AND if_data.ingredient = bm.ingredient
            AND bm.rn = 1
    ),
    
    recipe_totals AS (
        -- Agréger les totaux nutritionnels par recette
        SELECT 
            recipe_id,
            MAX(total_weight) AS total_weight,
            MAX(known_weight) AS known_weight,
            SUM(energy_kcal_total) AS energy_kcal_sum,
            SUM(protein_g_total) AS protein_g_sum,
            SUM(saturated_fats_g_total) AS saturated_fats_g_sum,
            SUM(fat_g_total) AS fat_g_sum,
            SUM(carb_g_total) AS carb_g_sum,
            SUM(fiber_g_total) AS fiber_g_sum,
            SUM(sugar_g_total) AS sugar_g_sum,
            SUM(sodium_mg_total) AS sodium_mg_sum,
            SUM(calcium_mg_total) AS calcium_mg_sum,
            SUM(iron_mg_total) AS iron_mg_sum,
            SUM(potassium_mg_total) AS potassium_mg_sum,
            SUM(vitc_mg_total) AS vitc_mg_sum,
            SUM(magnesium_mg_total) AS magnesium_mg_sum
        FROM ingredients_with_nutrition
        GROUP BY recipe_id
    )
    
    -- Convertir en valeurs pour 100g en utilisant GREATEST(total_weight, known_weight)
    SELECT 
        recipe_id AS id,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (energy_kcal_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS energy_kcal_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (protein_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS protein_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (saturated_fats_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS saturated_fats_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (fat_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS fat_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (carb_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS carb_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (fiber_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS fiber_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (sugar_g_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS sugar_g_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (sodium_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS sodium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (calcium_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS calcium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (iron_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS iron_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (potassium_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS potassium_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (vitc_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS vitc_mg_100g,
        CASE 
            WHEN GREATEST(total_weight, known_weight) > 0 
            THEN (magnesium_mg_sum / GREATEST(total_weight, known_weight)) * 100 
            ELSE NULL
        END AS magnesium_mg_100g
    FROM recipe_totals
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



ALTER TABLE NUTRIRAG_PROJECT.ENRICHED.RECIPES_SAMPLE_50K 
ADD COLUMN IF NOT EXISTS SCORE_SANTE FLOAT;


UPDATE NUTRIRAG_PROJECT.ENRICHED.RECIPES_SAMPLE_50K
SET SCORE_SANTE = CASE 
    WHEN ENERGY_KCAL_100G IS NULL THEN NULL
    ELSE GREATEST(0,
        (
            0.4 * (
                (
                    LEAST(COALESCE(PROTEIN_G_100G, 0) / 50, 1)
                    + LEAST(COALESCE(FIBER_G_100G, 0) / 30, 1)
                ) / 2
            )
            +
            0.4 * (
                (
                    CASE WHEN COALESCE(SUGAR_G_100G, 0) <= 50
                         THEN 1 - (COALESCE(SUGAR_G_100G, 0) / 50)
                         ELSE -1.2 * ((COALESCE(SUGAR_G_100G, 0) / 50) - 1)
                    END
                    +
                    CASE WHEN COALESCE(SATURATED_FATS_G_100G, 0) <= 20
                         THEN 1 - (COALESCE(SATURATED_FATS_G_100G, 0) / 20)
                         ELSE -1.0 * ((COALESCE(SATURATED_FATS_G_100G, 0) / 20) - 1)
                    END
                    +
                    CASE WHEN COALESCE(SODIUM_MG_100G, 0) <= 2000
                         THEN 1 - (COALESCE(SODIUM_MG_100G, 0) / 2000)
                         ELSE -1.5 * ((COALESCE(SODIUM_MG_100G, 0) / 2000) - 1)
                    END
                ) / 3
            )
            +
            0.2 * (
                (
                    LEAST(COALESCE(CALCIUM_MG_100G, 0) / 1000, 1)
                    + LEAST(COALESCE(IRON_MG_100G, 0) / 18, 1)
                    + LEAST(COALESCE(POTASSIUM_MG_100G, 0) / 3500, 1)
                    + LEAST(COALESCE(VITC_MG_100G, 0) / 90, 1)
                    + LEAST(COALESCE(MAGNESIUM_MG_100G, 0) / 350, 1)
                ) / 5 
            )
        ) * 100
    )
END;

-- Debug queries removed to avoid execution failures
