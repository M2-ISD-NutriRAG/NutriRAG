-- ==================================================================================
-- CLEAN RECIPES INGESTION - Server-side processing
-- ==================================================================================
-- This script creates cleaned recipe tables directly in Snowflake by:
-- 1. Joining raw tables (recipes, images, quantities)
-- 2. Parsing and filtering data
-- 3. Sampling for CLEANED (50K) and DEV_SAMPLE (1K) schemas
-- ==================================================================================

-- Step 1: Create full joined and filtered dataset
CREATE OR REPLACE TABLE {database}.{cleaned_schema}.{cleaned_table} AS
WITH base_recipes AS (
    SELECT 
        ID,
        NAME,
        MINUTES,
        CONTRIBUTOR_ID,
        SUBMITTED,
        TAGS,
        NUTRITION,
        N_STEPS,
        STEPS,
        DESCRIPTION,
        INGREDIENTS,
        N_INGREDIENTS,
        FILTERS
    FROM {database}.{raw_schema}.{raw_table}
    WHERE ID IS NOT NULL
),

images AS (
    SELECT 
        ID,
        IMAGE_URL,
        CASE 
            WHEN IMAGE_URL IS NOT NULL AND LENGTH(IMAGE_URL) > 0
            THEN 1 
            ELSE 0 
        END AS HAS_IMAGE
    FROM {database}.{raw_schema}.{recipes_enhanced_v2_table}
),

quantities AS (
    SELECT 
        ID,
        TO_VARCHAR(SERVING_SIZE) AS SERVING_SIZE,
        TRY_CAST(SERVINGS AS NUMBER(38,0)) AS SERVINGS,
        SEARCH_TERMS,
        INGREDIENTS_RAW_STR
    FROM {database}.{raw_schema}.{recipes_w_search_terms_table}
),

joined AS (
    SELECT 
        b.*,
        i.IMAGE_URL,
        i.HAS_IMAGE,
        q.SERVING_SIZE,
        q.SERVINGS,
        q.SEARCH_TERMS,
        q.INGREDIENTS_RAW_STR
    FROM base_recipes b
    LEFT JOIN images i ON b.ID = i.ID
    INNER JOIN quantities q ON b.ID = q.ID
)

SELECT *
FROM joined
WHERE 
    NAME IS NOT NULL 
    AND LENGTH(NAME) > 0
    AND MINUTES > 5
    AND ID IS NOT NULL
    AND ARRAY_SIZE(FILTERS) > 0
    AND SUBMITTED IS NOT NULL
    AND ARRAY_SIZE(TAGS) > 0
    AND ARRAY_SIZE(NUTRITION) = 7
    AND DESCRIPTION IS NOT NULL
    AND ARRAY_SIZE(STEPS) > 0
    AND ARRAY_SIZE(INGREDIENTS) > 0
;

-- Step 2: Create 50K sample for CLEANED schema
CREATE OR REPLACE TABLE {database}.{cleaned_schema}.{cleaned_table} AS
SELECT 
    NAME,
    ID,
    MINUTES,
    CONTRIBUTOR_ID,
    SUBMITTED,
    TAGS,
    NUTRITION,
    N_STEPS,
    STEPS,
    DESCRIPTION,
    INGREDIENTS,
    N_INGREDIENTS,
    HAS_IMAGE,
    IMAGE_URL,
    INGREDIENTS_RAW_STR,
    SERVING_SIZE,
    SERVINGS,
    SEARCH_TERMS,
    FILTERS
FROM {database}.{cleaned_schema}.{cleaned_table}
LIMIT 50000
;

-- Step 3: Create 1K sample for DEV schema
CREATE OR REPLACE TABLE {database}.{dev_schema}.RECIPES_SAMPLE_1K AS
SELECT 
    NAME,
    ID,
    MINUTES,
    CONTRIBUTOR_ID,
    SUBMITTED,
    TAGS,
    NUTRITION,
    N_STEPS,
    STEPS,
    DESCRIPTION,
    INGREDIENTS,
    N_INGREDIENTS,
    HAS_IMAGE,
    IMAGE_URL,
    INGREDIENTS_RAW_STR,
    SERVING_SIZE,
    SERVINGS,
    SEARCH_TERMS,
    FILTERS
FROM {database}.{cleaned_schema}.{cleaned_table}
LIMIT 1000
;
-- Step 3: Create 1K sample for DEV schema
CREATE OR REPLACE TABLE {database}.{dev_schema}.{cleaned_table} AS
SELECT 
    NAME,
    ID,
    MINUTES,
    CONTRIBUTOR_ID,
    SUBMITTED,
    TAGS,
    NUTRITION,
    N_STEPS,
    STEPS,
    DESCRIPTION,
    INGREDIENTS,
    N_INGREDIENTS,
    HAS_IMAGE,
    IMAGE_URL,
    INGREDIENTS_RAW_STR,
    SERVING_SIZE,
    SERVINGS,
    SEARCH_TERMS,
    FILTERS
FROM {database}.{cleaned_schema}.{cleaned_table};
