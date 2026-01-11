# LLM Evaluation Framework

A flexible framework for evaluating embedding models and configurations using either LLM-as-Judge or ground truth data, with support for multiple ranking metrics (Precision@K, NDCG@K, etc.).

## Project Structure

```
.
├── config/
│   └── config.json                          # Main configuration file for experiments
│
├── data/
│   ├── embedding_cache/                     # Cached embeddings to avoid recomputation
│   └── eval/
│       ├── ground_truth.json                # Ground truth labels for evaluation
│       └── query_test.json                  # Test queries for evaluation
│
├── notebooks/                               # notebooks for testing and exploration
│
├── prompts/                                 # Prompt templates for LLM-as-Judge
│   └── eval_prompt.txt                 # Prompt template for LLM judge evaluation
│
├── src/
│   ├── main.py                              # Main entry point for running experiments
│   └── pipeline/
│       ├── init_experience.py               # Initialize and configure experiments
│       ├── calculate_embeddings.py          # Generate and cache embeddings
│       ├── eval_llm_judge.py                # Evaluate LLM performance as judge
│       └── eval_embedding_model_config.py   # Evaluate embeddings and calculate metrics
│
└── README.md                                # This file
```

## File Descriptions

### Configuration Files

#### `config/config.json`
Main configuration file that controls all aspects of the experiment. Parameters are grouped by functionality:

**Experiment Identity**
- `Experiment_id`: Unique identifier for the experiment
- `raw_data_table_name`: Source table name in the database
- `number_row_analyse`: Number of rows to analyze from the dataset

**Evaluation Mode**
- `eval_with_llm_or_ground_truth`: Choose between `"llm"` (LLM-as-Judge) or `"ground_truth"` (manual labels)

**Input Data Paths**
- `input_raw_data_cache_file_path`: Cached raw data location
- `input_raw_data_file_path`: Raw data file name
- `input_embedding_cache_file_path`: Pre-computed embeddings cache
- `ground_truth_file_path`: Ground truth labels for evaluation
- `query_test_file_path`: Test queries for evaluation

**Directory Structure**
- `experiments_dir`: Root directory for experiment outputs (uses experiment_id)
- `config_dir`, `data_dir`, `raw_data_dir`, `embedding_data_dir`: Data organization directories
- `temp_data_dir`, `eval_data_dir`: Temporary and evaluation data storage
- `prompts_dir`: LLM prompt templates location
- `metrics_dir`, `llm_metrics_dir`, `embedding_metrics_dir`: Metrics output directories

**Output File Paths**
- `output_recipes_embedding_file_path`: Generated embeddings output
- `output_topk_model_query_retrieved_documents_file_path`: Top-K retrieved documents per model/query
- `output_retrived_documents_relevence_file_path`: Relevance scores for retrieved documents
- `output_topk_model_query_retrieved_documents_relevance_file_path`: Top-K documents with relevance
- `output_retrived_documents_metrics_file_path`: Per-query metrics
- `output_retrived_documents_aggregated_metrics_file_path`: Aggregated metrics across queries

**Override Flags** (control pipeline execution steps)
- `override_raw_data`: Re-download/reload raw data
- `override_embeddings`: Regenerate embeddings (ignore cache)
- `override_llm_eval`: Re-evaluate with LLM judge
- `override_documents_retrival`: Re-retrieve documents
- `override_embedding_eval`: Recalculate metrics

**Data Schema**
- `ID_column`: Column name for unique identifiers
- `data_columns`: List of available columns in the dataset (e.g., NAME, TAGS, INGREDIENTS, STEPS, DESCRIPTION, FILTERS)

**Embedding Configuration**
- `embedding_models`: List of embedding models to evaluate (e.g., `"thenlper/gte-small"`)
- `embedding_config`: Dictionary of column combinations to test
  - Each config (config_1, config_2, etc.) specifies which columns to concatenate for embedding
  - Allows testing different feature combinations for optimal retrieval

**LLM Judge Settings** (when using LLM-as-Judge mode)
- `llm_model`: Model name for LLM judge (e.g., `"mistral-large2"`)
- `temperature`: Sampling temperature for LLM responses
- `max_tokens`: Maximum tokens per LLM response
- `context_window`: Total context window size
- `number_doc_per_call`: Documents to evaluate per LLM call
- `max_retries_llm_calls`: Retry attempts for failed LLM calls
- `llm_json_schema`: Expected JSON structure for LLM judge output (relevance scores and justifications)
- `eval_prompt_file_path`: Path to LLM judge prompt template
- `eval_llm_ground_truth_file_path`: Ground truth for validating LLM judge quality

**Top-k**
- `top_k`: List of K values for computing Precision@K, NDCG@K, etc. (e.g., [1, 3, 5, 10, 20])

### Data Files

#### `data/eval/ground_truth.json`
Ground truth labels for evaluation queries. Used when `use_llm_judge: false`.

#### `data/eval/query_test.json`
Test queries to evaluate against the embedding configurations.

#### `data/embedding_cache/`
Directory storing cached embeddings to avoid redundant computations across experiments.

### Pipeline Modules

#### `src/pipeline/init_experience.py`
- Initializes experiment environment
- Validates configuration
- Sets up necessary directories and logging

#### `src/pipeline/calculate_embeddings.py`
- Generates embeddings for specified models and columns
- Implements caching mechanism
- Handles multiple embedding model configurations

#### `src/pipeline/eval_llm_judge.py`
- Evaluates LLM performance before using it as judge
- Validates LLM judge reliability
- Generates judge quality metrics (

#### `src/pipeline/eval_embedding_model_config.py`
- Main evaluation pipeline
- Calculates ranking metrics: Precision@K, NDCG@K, MAP@K, MRR@K
- Supports both ground truth and LLM-as-Judge evaluation modes

#### `src/main.py`
- Launch the entire pipeline



