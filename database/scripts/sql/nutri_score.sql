-- Créer la table ENRICHED.INGREDIENTS en copiant depuis ANALYTICS
CREATE OR REPLACE TABLE {database}.{enriched_schema}.INGREDIENTS AS
SELECT *
FROM NUTRIRAG_PROJECT.{analytics_schema}.INGREDIENTS_WITH_CLUSTERS;

-- Ajouter la colonne SCORE_SANTE si elle n'existe pas déjà
ALTER TABLE {database}.{enriched_schema}.INGREDIENTS 
ADD COLUMN IF NOT EXISTS SCORE_SANTE FLOAT;

-- Recalculer SCORE_SANTE dans la table ENRICHED
UPDATE {database}.{enriched_schema}.INGREDIENTS
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


