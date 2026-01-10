-- ==================================================================================
-- EXTRACT FILTERS UDF - Map recipe tags to dietary/dietary restriction filters
-- ==================================================================================
-- This UDF takes an array of recipe tags and maps them to standardized filter categories
-- Categories include: vegan, vegetarian, kosher, egg_free, dairy_free, gluten_free, etc.

CREATE OR REPLACE FUNCTION {database}.{raw_schema}.EXTRACT_FILTERS(tags ARRAY)
RETURNS ARRAY
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
HANDLER = 'extract_filters'
AS $$
def extract_filters(tags):
    if not tags:
        return []
    
    # Mapping of tags to filter categories
    tag_to_filter = {{
        "vegan": "vegan",
        "vegetarian": "vegetarian",
        "veggie": "vegetarian",
        "veggie-burgers": "vegetarian",
        "no meat": "vegetarian",
        "meatless": "vegetarian",

        "kosher": "kosher",
        "jewish-ashkenazi": "kosher",
        "jewish": "kosher",
        "hanukkah": "kosher",

        "egg-free": "egg_free",
        "dairy-free": "dairy_free",
        "salt-free": "salt_free",
        "flour-less": "flour_less",
        "flourless": "flour_less",
        "no flour": "flour_less",
        "grain-free": "grain_free",
        "sugar-free": "sugar_free",
        "sugarless": "sugar_free",
        "carb-free": "carb_free",
        "low-carb": "low_carb",
        "very-low-carbs": "low_carb",
        "low-cholesterol": "low_cholesterol",
        "low-protein": "low_protein",
        "low-calorie": "low_calorie",
        "low-calories": "low_calorie",
        "low-saturated-fat": "low_saturated_fat",
        "gluten-free": "gluten_free",
        "fat-free": "fat_free",
        "no-shell-fish": "no_shell_fish",
        "diabetic": "diabetic",
        "low-sodium": "low_sodium",
        "nut-free": "nut_free",
        "low-fat": "low_fat",

        "ramadan": "halal",

        "amish-mennonite": "amish",

        "non-alcoholic": "non_alcoholic"
    }}
    
    # Extract unique filters from tags
    filters = []
    seen = set()
    
    for tag in tags:
        tag_lower = tag.lower()
        
        if tag_lower in tag_to_filter:
            filter_val = tag_to_filter[tag_lower]
            if filter_val not in seen:
                filters.append(filter_val)
                seen.add(filter_val)
    
    return filters
$$;

-- ==================================================================================
-- Add FILTERS column to RAW table if it doesn't exist
-- ==================================================================================

ALTER TABLE {database}.{raw_schema}.{raw_table}
ADD COLUMN IF NOT EXISTS FILTERS ARRAY;

-- ==================================================================================
-- Update FILTERS column in RAW table
-- ==================================================================================

UPDATE {database}.{raw_schema}.{raw_table}
SET FILTERS = {database}.{raw_schema}.EXTRACT_FILTERS(TAGS)
WHERE FILTERS IS NULL OR ARRAY_SIZE(FILTERS) = 0;
