"""Snowflake table definitions for INGREDIENTS_QUANTITY, INGREDIENTS_TAGGED and INGREDIENTS_MATCHING tables."""


from shared.snowflake.tables.table import define_snowflake_table, Table


@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="RAW",
    TABLE_NAME="INGREDIENTS_QUANTITY",
)
class ParsingIngredientsTable(Table):
    ID_RECIPE = "ID_RECIPE"
    INGREDIENT = "INGREDIENT"
    QUANTITY_RAW_STR = "QUANTITY_RAW_STR"
    QUANTITY = "QUANTITY"
    UNIT = "UNIT"
    QTY_ML = "QTY_ML"
    QTY_G = "QTY_G"


@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="CLEANED",
    TABLE_NAME="INGREDIENTS_MATCHING",
)
class MatchingIngredientsTable(Table):
    ID = "ID"
    INGREDIENT = "INGREDIENT"
    NDB_NO = "NDB_NO"

@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="CLEANED",
    TABLE_NAME="INGREDIENTS_TAGGED",
)
class IngredientsTagged(Table):
    CONTAINS_NUTS = "CONTAINS_NUTS"
    DESCRIP = "DESCRIP"
    FOODON_LABEL = "FOODON_LABEL"
    IS_DAIRY = "IS_DAIRY"
    IS_GLUTEN = "IS_GLUTEN"
    IS_GRAIN = "IS_GRAIN"
    IS_SEAFOOD = "IS_SEAFOOD"
    IS_SWEETENER = "IS_SWEETENER"
    IS_VEGETABLE = "IS_VEGETABLE"
    IS_VEGETARIAN = "IS_VEGETARIAN"
    NDB_NO = "NDB_NO"
