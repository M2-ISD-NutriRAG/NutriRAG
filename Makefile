.PHONY: help run clean

# Default target
help:
	@echo "🍽️  NutriRAG Pipeline"
	@echo ""
	@echo "  make run                   Run the full pipeline (all data)"
	@echo "  make clean                 Clean up temporary files"
	@echo ""

# Run the full pipeline with all data
run:
	@echo "🚀 Starting NutriRAG pipeline - processing all data..."
	cd database/scripts/python && python main.py

# Clean temporary files
clean:
	@echo "🧹 Cleaning up temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

.DEFAULT_GOAL := help
