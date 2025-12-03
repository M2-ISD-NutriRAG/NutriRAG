"""Snowflake table definitions for INGREDIENTS_QUANTITY, Ingredients Tagged and INGREDIENTS_MATCHING tables."""

from typing import List

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
