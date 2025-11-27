"""
Contract tests for the search schema.

These tests ensure that the search schema adheres to the defined contract,
validating both the structure and data types of the search results.
"""

import pytest
from pydantic import ValidationError
from app.models.search import (
    SearchFilters,
    SearchRequest,
    SearchResult,
    SearchResponse,
)


# ==============================================================================
# SearchFilters Contract Tests
# ==============================================================================


@pytest.mark.contract
class TestSearchFiltersValidation:
    """Test SearchFilters validation rules and boundaries."""

    def test_filters_accepts_all_optional_fields_as_none(self):
        """SearchFilters should accept all fields as None (empty filter)."""
        filters = SearchFilters()

        # Nutrition filters should all be None
        assert filters.calories_min is None
        assert filters.calories_max is None
        assert filters.total_fat_min is None
        assert filters.total_fat_max is None
        assert filters.sugar_min is None
        assert filters.sugar_max is None
        assert filters.sodium_min is None
        assert filters.sodium_max is None
        assert filters.protein_min is None
        assert filters.protein_max is None
        assert filters.saturated_fat_min is None
        assert filters.saturated_fat_max is None
        assert filters.carbs_min is None
        assert filters.carbs_max is None

        # Recipe attributes filters should all be None
        assert filters.minutes_min is None
        assert filters.minutes_max is None
        assert filters.n_steps_min is None
        assert filters.n_steps_max is None
        assert filters.n_ingredients_min is None
        assert filters.n_ingredients_max is None
        assert filters.servings_min is None
        assert filters.servings_max is None
        assert filters.serving_size_min is None
        assert filters.serving_size_max is None

        # Tags and ingredients filters should all be None
        assert filters.tags_include is None
        assert filters.tags_exclude is None
        assert filters.ingredients_include is None
        assert filters.ingredients_exclude is None

        # Rating filters should all be None
        assert filters.rating_avg_min is None
        assert filters.rating_avg_max is None
        assert filters.rating_count_min is None

    @pytest.mark.parametrize(
        "field,value",
        [
            # Nutrition filters
            ("calories_min", -100.0),
            ("calories_max", -50.0),
            ("total_fat_min", -10.0),
            ("total_fat_max", -5.0),
            ("sugar_min", -15.0),
            ("sugar_max", -10.0),
            ("sodium_min", -200.0),
            ("sodium_max", -100.0),
            ("protein_min", -20.0),
            ("protein_max", -10.0),
            ("saturated_fat_min", -5.0),
            ("saturated_fat_max", -3.0),
            ("carbs_min", -30.0),
            ("carbs_max", -15.0),
            # Recipe attributes filters
            ("minutes_min", -5),
            ("minutes_max", -10),
            ("n_steps_min", -2),
            ("n_steps_max", -5),
            ("n_ingredients_min", -1),
            ("n_ingredients_max", -3),
            ("servings_min", -2),
            ("servings_max", -4),
            ("serving_size_min", -10.0),
            ("serving_size_max", -5.0),
            # Rating filters
            ("rating_avg_min", -2.0),
            ("rating_avg_max", -1.0),
            ("rating_count_min", -10),
        ],
    )
    def test_filters_rejects_negative_values(self, field, value):
        """Numeric fields must reject negative values."""
        with pytest.raises(ValidationError):
            SearchFilters(**{field: value})

    @pytest.mark.parametrize(
        "field,value",
        [
            ("rating_avg_min", 6.0),
            ("rating_avg_max", 5.5),
        ],
    )
    def test_filters_rejects_rating_above_maximum(self, field, value):
        """Rating fields must reject values above 5."""
        with pytest.raises(ValidationError):
            SearchFilters(**{field: value})

    def test_filters_accepts_valid_rating_range(self):
        """SearchFilters should accept rating values between 0 and 5."""
        filters = SearchFilters(rating_avg_min=0.0, rating_avg_max=5.0)
        assert filters.rating_avg_min == 0.0
        assert filters.rating_avg_max == 5.0


@pytest.mark.contract
class TestSearchFiltersMinMaxValidation:
    """Test SearchFilters min/max range validation logic."""

    @pytest.mark.parametrize(
        "min_field,max_field,min_val,max_val",
        [
            # Nutrition filters
            ("calories_min", "calories_max", 500.0, 200.0),
            ("total_fat_min", "total_fat_max", 50.0, 20.0),
            ("sugar_min", "sugar_max", 30.0, 10.0),
            ("sodium_min", "sodium_max", 1000.0, 500.0),
            ("protein_min", "protein_max", 50.0, 20.0),
            ("saturated_fat_min", "saturated_fat_max", 20.0, 10.0),
            ("carbs_min", "carbs_max", 100.0, 50.0),
            # Recipe attributes filters
            ("minutes_min", "minutes_max", 60, 30),
            ("n_steps_min", "n_steps_max", 10, 5),
            ("n_ingredients_min", "n_ingredients_max", 20, 10),
            ("servings_min", "servings_max", 10, 5),
            ("serving_size_min", "serving_size_max", 500.0, 200.0),
            # Rating filters
            ("rating_avg_min", "rating_avg_max", 4.5, 3.0),
        ],
    )
    def test_filters_rejects_min_greater_than_max(
        self, min_field, max_field, min_val, max_val
    ):
        """Min/max pairs must satisfy min <= max constraint."""
        with pytest.raises(ValidationError):
            SearchFilters(**{min_field: min_val, max_field: max_val})

    @pytest.mark.parametrize(
        "min_field,max_field,min_val,max_val",
        [
            # Nutrition filters
            ("calories_min", "calories_max", 300.0, 300.0),
            ("total_fat_min", "total_fat_max", 50.0, 50.0),
            ("sugar_min", "sugar_max", 30.0, 30.0),
            ("sodium_min", "sodium_max", 1000.0, 1000.0),
            ("protein_min", "protein_max", 25.0, 25.0),
            ("saturated_fat_min", "saturated_fat_max", 10.0, 10.0),
            ("carbs_min", "carbs_max", 80.0, 80.0),
            # Recipe attributes filters
            ("minutes_min", "minutes_max", 45, 45),
            ("n_steps_min", "n_steps_max", 8, 8),
            ("n_ingredients_min", "n_ingredients_max", 15, 15),
            ("servings_min", "servings_max", 2, 2),
            ("serving_size_min", "serving_size_max", 300.0, 300.0),
            # Rating filters
            ("rating_avg_min", "rating_avg_max", 4.0, 4.0),
        ],
    )
    def test_filters_accepts_equal_min_and_max_values(
        self, min_field, max_field, min_val, max_val
    ):
        """SearchFilters should accept when min equals max (exact match)."""
        filters = SearchFilters(**{min_field: min_val, max_field: max_val})
        assert getattr(filters, min_field) == min_val
        assert getattr(filters, max_field) == max_val

    def test_filters_accepts_valid_ranges_for_all_nutrients(self):
        """SearchFilters should accept valid ranges for all nutritional fields."""
        filters = SearchFilters(
            calories_min=200.0,
            calories_max=500.0,
            total_fat_min=10.0,
            total_fat_max=30.0,
            sugar_min=0.0,
            sugar_max=15.0,
            sodium_min=0.0,
            sodium_max=500.0,
            protein_min=20.0,
            protein_max=50.0,
            saturated_fat_min=0.0,
            saturated_fat_max=10.0,
            carbs_min=30.0,
            carbs_max=100.0,
        )
        assert filters.calories_min == 200.0
        assert filters.calories_max == 500.0
        assert filters.total_fat_min == 10.0
        assert filters.total_fat_max == 30.0
        assert filters.sugar_min == 0.0
        assert filters.sugar_max == 15.0
        assert filters.sodium_min == 0.0
        assert filters.sodium_max == 500.0
        assert filters.protein_min == 20.0
        assert filters.protein_max == 50.0
        assert filters.saturated_fat_min == 0.0
        assert filters.saturated_fat_max == 10.0
        assert filters.carbs_min == 30.0
        assert filters.carbs_max == 100.0

    def test_filters_accepts_valid_ranges_for_all_recipe_attributes(self):
        """SearchFilters should accept valid ranges for all recipe attribute fields."""
        filters = SearchFilters(
            minutes_min=10,
            minutes_max=60,
            n_steps_min=2,
            n_steps_max=10,
            n_ingredients_min=5,
            n_ingredients_max=20,
            servings_min=1,
            servings_max=8,
            serving_size_min=100.0,
            serving_size_max=500.0,
        )
        assert filters.minutes_min == 10
        assert filters.minutes_max == 60
        assert filters.n_steps_min == 2
        assert filters.n_steps_max == 10
        assert filters.n_ingredients_min == 5
        assert filters.n_ingredients_max == 20
        assert filters.servings_min == 1
        assert filters.servings_max == 8
        assert filters.serving_size_min == 100.0
        assert filters.serving_size_max == 500.0

    def test_filters_accepts_valid_ranges_for_ratings(self):
        """SearchFilters should accept valid ranges for all rating fields."""
        filters = SearchFilters(
            rating_avg_min=2.0,
            rating_avg_max=4.5,
        )
        assert filters.rating_avg_min == 2.0
        assert filters.rating_avg_max == 4.5


@pytest.mark.contract
class TestSearchFiltersListFields:
    """Test SearchFilters list field behaviors."""

    def test_tags_filters_accepts_empty_lists(self):
        """SearchFilters should accept empty lists for tags."""
        filters = SearchFilters(tags_include=[], tags_exclude=[])
        assert filters.tags_include == []
        assert filters.tags_exclude == []

    def test_ingredients_filters_accepts_empty_lists(self):
        """SearchFilters should accept empty lists for ingredients."""
        filters = SearchFilters(ingredients_include=[], ingredients_exclude=[])
        assert filters.ingredients_include == []
        assert filters.ingredients_exclude == []

    def test_tags_filters_accepts_multiple_tags(self):
        """SearchFilters should accept multiple tags in include/exclude lists."""
        filters = SearchFilters(
            tags_include=["vegetarian", "healthy", "quick"],
            tags_exclude=["dairy", "nuts"],
        )
        assert len(filters.tags_include) == 3
        assert len(filters.tags_exclude) == 2

        assert "vegetarian" in filters.tags_include
        assert "healthy" in filters.tags_include
        assert "quick" in filters.tags_include

        assert "dairy" in filters.tags_exclude
        assert "nuts" in filters.tags_exclude

    def test_ingredients_filters_accepts_multiple_ingredients(self):
        """SearchFilters should accept multiple ingredients in include/exclude lists."""
        filters = SearchFilters(
            ingredients_include=["chicken", "garlic", "onion"],
            ingredients_exclude=["gluten", "dairy"],
        )
        assert len(filters.ingredients_include) == 3
        assert len(filters.ingredients_exclude) == 2

        assert "chicken" in filters.ingredients_include
        assert "garlic" in filters.ingredients_include
        assert "onion" in filters.ingredients_include

        assert "gluten" in filters.ingredients_exclude
        assert "dairy" in filters.ingredients_exclude

    def test_tags_filters_preserve_order(self):
        """SearchFilters should preserve the order of items in lists."""
        filters = SearchFilters(
            tags_include=["healthy", "vegetarian", "quick", "easy"],
            tags_exclude=["dairy", "nuts"],
        )
        assert filters.tags_include == ["healthy", "vegetarian", "quick", "easy"]
        assert filters.tags_exclude == ["dairy", "nuts"]

    def test_ingredients_filters_preserve_order(self):
        """SearchFilters should preserve the order of items in ingredient lists."""
        filters = SearchFilters(
            ingredients_include=["chicken", "garlic", "onion", "tomato"],
            ingredients_exclude=["gluten", "dairy"],
        )
        assert filters.ingredients_include == ["chicken", "garlic", "onion", "tomato"]
        assert filters.ingredients_exclude == ["gluten", "dairy"]


# ==============================================================================
# SearchRequest Contract Tests
# ==============================================================================


@pytest.mark.contract
class TestSearchRequestValidation:
    """Test SearchRequest validation rules."""

    def test_request_requires_query_field(self):
        """SearchRequest should require a query field."""
        with pytest.raises(ValidationError):
            SearchRequest()

    def test_request_rejects_empty_query(self):
        """SearchRequest should reject empty query strings."""
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_request_accepts_query_without_filters(self):
        """SearchRequest should accept query without filters."""
        request = SearchRequest(query="pasta recipes")
        assert request.query == "pasta recipes"
        assert request.filters is None
        assert request.limit == 10  # default value

    def test_request_accepts_query_with_filters(self):
        """SearchRequest should accept query with optional filters."""
        filters = SearchFilters(calories_max=500.0)
        request = SearchRequest(query="healthy meals", filters=filters)
        assert request.query == "healthy meals"
        assert request.filters == filters

    def test_request_has_default_limit_of_10(self):
        """SearchRequest should default to limit of 10 results."""
        request = SearchRequest(query="test")
        assert request.limit == 10

    def test_request_accepts_custom_limit(self):
        """SearchRequest should accept custom limit values."""
        request = SearchRequest(query="test", limit=25)
        assert request.limit == 25

    def test_request_rejects_limit_below_minimum(self):
        """SearchRequest should reject limit values below 1."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)

    def test_request_rejects_limit_above_maximum(self):
        """SearchRequest should reject limit values above 50."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=51)

    def test_request_accepts_boundary_limit_values(self):
        """SearchRequest should accept limit values at boundaries (1 and 50)."""
        request_min = SearchRequest(query="test", limit=1)
        request_max = SearchRequest(query="test", limit=50)
        assert request_min.limit == 1
        assert request_max.limit == 50


# ==============================================================================
# SearchResult Contract Tests
# ==============================================================================


@pytest.mark.contract
class TestSearchResultValidation:
    """Test SearchResult validation rules."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"name": "Test Recipe", "similarity": 0.95},
            {"id": 123, "similarity": 0.95},
            {"id": 123, "name": "Test Recipe"},
            {},
        ],
    )
    def test_result_requires_id_name_and_similarity(self, kwargs):
        """SearchResult should require id, name, and similarity fields."""
        with pytest.raises(ValidationError):
            SearchResult(**kwargs)

    def test_result_rejects_empty_name(self):
        """SearchResult should reject empty recipe names."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="", similarity=0.95)

    def test_result_accepts_minimal_valid_data(self):
        """SearchResult should accept minimal valid data (required fields only)."""
        result = SearchResult(id=123, name="Pasta Recipe", similarity=0.85)
        assert result.id == 123
        assert result.name == "Pasta Recipe"
        assert result.description is None
        assert result.tags is None
        assert result.minutes is None
        assert result.nutrition is None
        assert result.score_health is None
        assert result.n_ingredients is None
        assert result.ingredients is None
        assert result.n_steps is None
        assert result.steps is None
        assert result.servings is None
        assert result.serving_size is None
        assert result.rating_avg is None
        assert result.rating_count is None
        assert result.similarity == 0.85

    def test_result_rejects_negative_id(self):
        """SearchResult should reject negative recipe IDs."""
        with pytest.raises(ValidationError):
            SearchResult(id=-1, name="Test", similarity=0.5)

    def test_similarity_field_should_be_between_0_and_1(self):
        """SearchResult similarity field should be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=1.5)

        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=-0.1)

        result_min = SearchResult(id=1, name="Test1", similarity=0.0)
        result_max = SearchResult(id=2, name="Test2", similarity=1.0)
        assert result_min.similarity == 0.0
        assert result_max.similarity == 1.0

        result_mid = SearchResult(id=3, name="Test3", similarity=0.75)
        assert result_mid.similarity == 0.75

    def test_minutes_field_should_be_positive_if_provided(self):
        """SearchResult minutes field should be positive if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, minutes=-5)

        result = SearchResult(id=1, name="Test", similarity=0.9, minutes=30)
        assert result.minutes == 30

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, minutes=0)
        assert result_zero.minutes == 0

    def test_score_health_field_should_be_between_0_and_1_if_provided(self):
        """SearchResult score_health field should be between 0 and 1 if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, score_health=-0.1)

        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, score_health=1.5)

        result = SearchResult(id=1, name="Test", similarity=0.9, score_health=0.75)
        assert result.score_health == 0.75

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, score_health=0.0)
        assert result_zero.score_health == 0.0

        result_one = SearchResult(id=1, name="Test", similarity=0.9, score_health=1.0)
        assert result_one.score_health == 1.0

    def test_n_ingredients_field_should_be_positive_if_provided(self):
        """SearchResult n_ingredients field should be positive if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, n_ingredients=-3)

        result = SearchResult(id=1, name="Test", similarity=0.9, n_ingredients=5)
        assert result.n_ingredients == 5

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, n_ingredients=0)
        assert result_zero.n_ingredients == 0

    def test_n_steps_field_should_be_positive_if_provided(self):
        """SearchResult n_steps field should be positive if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, n_steps=-2)

        result = SearchResult(id=1, name="Test", similarity=0.9, n_steps=4)
        assert result.n_steps == 4

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, n_steps=0)
        assert result_zero.n_steps == 0

    def test_servings_field_should_be_larger_than_one_if_provided(self):
        """SearchResult servings field should be larger than one if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, servings=0)

        result = SearchResult(id=1, name="Test", similarity=0.9, servings=4)
        assert result.servings == 4

        result_one = SearchResult(id=1, name="Test", similarity=0.9, servings=1)
        assert result_one.servings == 1

    def test_serving_size_field_should_be_positive_if_provided(self):
        """SearchResult serving_size field should be positive if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, serving_size=-10.0)

        result = SearchResult(id=1, name="Test", similarity=0.9, serving_size=150.0)
        assert result.serving_size == 150.0

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, serving_size=0.0)
        assert result_zero.serving_size == 0.0

    def test_rating_avg_field_should_be_between_0_and_5_if_provided(self):
        """SearchResult rating_avg field should be between 0 and 5 if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_avg=-1.0)

        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_avg=6.0)

        result = SearchResult(id=1, name="Test", similarity=0.9, rating_avg=4.2)
        assert result.rating_avg == 4.2

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, rating_avg=0.0)
        assert result_zero.rating_avg == 0.0

        result_five = SearchResult(id=1, name="Test", similarity=0.9, rating_avg=5.0)
        assert result_five.rating_avg == 5.0

    def test_rating_count_field_should_be_positive_if_provided(self):
        """SearchResult rating_count field should be positive if provided."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_count=-20)

        result = SearchResult(id=1, name="Test", similarity=0.9, rating_count=150)
        assert result.rating_count == 150

        result_zero = SearchResult(id=1, name="Test", similarity=0.9, rating_count=0)
        assert result_zero.rating_count == 0


@pytest.mark.contract
class TestSearchResultOptionalFields:
    """Test SearchResult optional field behaviors."""

    def test_result_rejects_negative_minutes(self):
        """SearchResult should reject negative cooking time."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, minutes=-10)

    def test_result_rejects_negative_n_ingredients(self):
        """SearchResult should reject negative ingredient counts."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, n_ingredients=-5)

    def test_result_rejects_negative_n_steps(self):
        """SearchResult should reject negative step counts."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, n_steps=-2)

    def test_result_rejects_servings_below_minimum(self):
        """SearchResult should reject servings below 1."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, servings=0)

    def test_result_rejects_negative_serving_size(self):
        """SearchResult should reject negative serving sizes."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, serving_size=-5.0)

    def test_result_rejects_rating_above_maximum(self):
        """SearchResult should reject rating values above 5.0."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_avg=5.5)

    def test_result_rejects_negative_rating(self):
        """SearchResult should reject negative rating values."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_avg=-1.0)

    def test_result_rejects_negative_rating_count(self):
        """SearchResult should reject negative rating counts."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, rating_count=-10)

    def test_result_rejects_health_score_above_maximum(self):
        """SearchResult should reject health scores above 1.0."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, score_health=1.5)

    def test_result_rejects_negative_health_score(self):
        """SearchResult should reject negative health scores."""
        with pytest.raises(ValidationError):
            SearchResult(id=1, name="Test", similarity=0.9, score_health=-0.1)

    def test_result_accepts_all_optional_fields(self):
        """SearchResult should accept all optional fields when provided."""
        result = SearchResult(
            id=42,
            name="Complete Recipe",
            similarity=0.92,
            description="A delicious recipe",
            tags=["healthy", "quick"],
            minutes=30,
            nutrition={"calories": 350.0, "protein": 25.0},
            score_health=0.85,
            n_ingredients=10,
            ingredients=["chicken", "rice", "vegetables"],
            n_steps=5,
            steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            servings=4,
            serving_size=250.0,
            rating_avg=4.5,
            rating_count=127,
        )
        assert result.id == 42
        assert result.description == "A delicious recipe"
        assert len(result.tags) == 2
        assert result.nutrition["calories"] == 350.0
        assert len(result.ingredients) == 3
        assert len(result.steps) == 5


@pytest.mark.contract
class TestSearchResultDataStructures:
    """Test SearchResult complex data structure behaviors."""

    def test_result_accepts_empty_lists(self):
        """SearchResult should accept empty lists for list fields."""
        result = SearchResult(
            id=1,
            name="Test",
            similarity=0.9,
            tags=[],
            ingredients=[],
            steps=[],
        )
        assert result.tags == []
        assert result.ingredients == []
        assert result.steps == []

    def test_result_accepts_complex_nutrition_dict(self):
        """SearchResult should accept complex nutrition dictionaries."""
        nutrition = {
            "calories": 450.0,
            "protein": 30.0,
            "carbs": 45.0,
            "fat": 15.0,
            "fiber": 8.0,
            "sugar": 5.0,
        }
        result = SearchResult(id=1, name="Test", similarity=0.9, nutrition=nutrition)
        assert result.nutrition == nutrition
        assert result.nutrition["protein"] == 30.0


# ==============================================================================
# SearchResponse Contract Tests
# ==============================================================================


@pytest.mark.contract
class TestSearchResponseValidation:
    """Test SearchResponse validation rules."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"query": "test query", "total_found": 5, "execution_time_ms": 100.0},
            {"results": [], "total_found": 0, "execution_time_ms": 50.0},
            {"results": [], "query": "test query", "execution_time_ms": 75.0},
            {"results": [], "query": "test query", "total_found": 0},
            {},
        ],
    )
    def test_response_requires_all_mandatory_fields(self, kwargs):
        """SearchResponse should require results, query, total_found, and execution_time_ms."""
        with pytest.raises(ValidationError):
            SearchResponse(**kwargs)

    def test_response_accepts_empty_results_list(self):
        """SearchResponse should accept empty results list (no matches found)."""
        response = SearchResponse(
            results=[],
            query="nonexistent recipe",
            total_found=0,
            execution_time_ms=45.2,
        )
        assert response.results == []
        assert response.total_found == 0

    def test_response_accepts_multiple_results(self):
        """SearchResponse should accept multiple search results."""
        results = [
            SearchResult(id=1, name="Recipe 1", similarity=0.95),
            SearchResult(id=2, name="Recipe 2", similarity=0.87),
            SearchResult(id=3, name="Recipe 3", similarity=0.72),
        ]
        response = SearchResponse(
            results=results,
            query="pasta",
            total_found=3,
            execution_time_ms=123.4,
        )
        assert len(response.results) == 3
        assert response.total_found == 3

    def test_response_rejects_negative_total_found(self):
        """SearchResponse should reject negative total_found values."""
        with pytest.raises(ValidationError):
            SearchResponse(
                results=[],
                query="test",
                total_found=-1,
                execution_time_ms=50.0,
            )

    def test_response_rejects_negative_execution_time(self):
        """SearchResponse should reject negative execution times."""
        with pytest.raises(ValidationError):
            SearchResponse(
                results=[],
                query="test",
                total_found=0,
                execution_time_ms=-10.5,
            )

    def test_response_accepts_zero_execution_time(self):
        """SearchResponse should accept zero execution time (cached results)."""
        response = SearchResponse(
            results=[],
            query="test",
            total_found=0,
            execution_time_ms=0.0,
        )
        assert response.execution_time_ms == 0.0

    def test_response_accepts_valid_complete_response(self):
        """SearchResponse should accept a complete valid response."""
        results = [
            SearchResult(
                id=1,
                name="Healthy Pasta",
                similarity=0.95,
                tags=["healthy", "quick"],
                minutes=20,
                rating_avg=4.5,
            )
        ]
        response = SearchResponse(
            results=results,
            query="healthy pasta recipes",
            total_found=1,
            execution_time_ms=87.3,
        )
        assert len(response.results) == 1
        assert response.query == "healthy pasta recipes"
        assert response.total_found == 1
        assert response.execution_time_ms == 87.3


# ==============================================================================
# Edge Cases: Boundary Value Tests
# ==============================================================================


@pytest.mark.contract
class TestBoundaryValues:
    """Test extreme boundary values and edge cases."""

    def test_filters_accepts_zero_for_all_min_fields(self):
        """All min fields should accept 0 as valid minimum boundary."""
        filters = SearchFilters(
            calories_min=0.0,
            total_fat_min=0.0,
            sugar_min=0.0,
            sodium_min=0.0,
            protein_min=0.0,
            saturated_fat_min=0.0,
            carbs_min=0.0,
            minutes_min=0,
            n_steps_min=0,
            n_ingredients_min=0,
            servings_min=0,
            serving_size_min=0.0,
            rating_count_min=0,
            rating_avg_min=0.0,
        )
        assert filters.calories_min == 0.0
        assert filters.minutes_min == 0
        assert filters.rating_avg_min == 0.0

    def test_filters_accepts_precise_decimal_values(self):
        """Filters should preserve precise decimal values."""
        filters = SearchFilters(
            calories_min=123.456789,
            protein_max=45.123456,
            rating_avg_min=3.14159,
        )
        assert filters.calories_min == pytest.approx(123.456789)
        assert filters.protein_max == pytest.approx(45.123456)
        assert filters.rating_avg_min == pytest.approx(3.14159)

    def test_result_accepts_precise_similarity_values(self):
        """SearchResult should preserve precise similarity scores."""
        result = SearchResult(
            id=1,
            name="Test",
            similarity=0.987654321,
        )
        assert result.similarity == pytest.approx(0.987654321)
