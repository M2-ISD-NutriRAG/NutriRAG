# 🍲 Recipe Embedding and Retrieval Evaluation Project

This project focuses on generating vector **embeddings** for recipe data and **evaluating** their performance in a retrieval context. It allows for systematic experimentation with different embedding models and combinations of data columns.

## 📂 Project Structure Hierarchy

The following diagram illustrates the project's key file and folder organization:



---

## ⚙️ Configuration and Environment

### 🔒 `.env` File (Environment Variables)

This file stores sensitive database credentials and project-specific parameters. **It MUST be added to `.gitignore`.**

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `USER` | Database User Name | `MY_USER` |
| `PASSWORD` | Database Password | `secure_password` |
| `PASSCODE` | MFA Passcode (if required) | `123456` |
| `ACCOUNT` | Database Account Identifier | `xy12345.eu-central-1` |
| `WAREHOUSE` | Database Warehouse Name | `COMPUTE_WH` |
| `DATABASE` | Database Name | `RECIPE_DB` |
| `SCHEMA` | Database Schema Name | `PUBLIC` |
| `TABLE` | Database Table Name | `RECIPES` |
| `CONFIG_FILE_PATH` | Path to the main configuration file for experiments | `"config/base_config.json"` |

### 🛠️ Utility Files

| File | Purpose |
| :--- | :--- |
| **`requirements.txt`** | Lists all necessary **Python package dependencies** required to run the project. |
| **`config/base_config.json`** | The main **configuration file** used to define which columns to embed and which embedding models to test. |

---

## 📓 Notebooks (Execution Workflow)

The project workflow is managed by two primary Jupyter notebooks:

### 1. `create_embedding.ipynb`

* **Purpose**: Handles the process of **generating vector embeddings**.
* **Workflow**: Reads the raw data from `data/`, applies the embedding logic (as defined by the configuration in `config/base_config.json`), and saves the resulting embeddings to an experiment-specific folder in `experiments/`.

### 2. `eval_embedding_model_config.ipynb`

* **Purpose**: Orchestrates the systematic **evaluation of different models and column combinations**.
* **Workflow**: Iterates through models and column combinations defined in the configuration, performs the retrieval search using the embeddings, calculates metrics against the ground truth queries, and saves the results to the `metrics/` subfolder within each experiment.

---

## 💾 Data and Ground Truth

### 📂 `data/`

* **Content**: Contains the raw dataset.
* **Dataset**: A dataset of **1,000 recipes** used for embedding generation.

### 📂 `query/`

* **Content**: Contains the **ground truth for retrieval evaluation**.
* **File (`query/query_test`)**: A JSON file/structure containing a list of objects. Each object includes a `query_text` and a list of `documents` (recipe IDs) that are **relevant ground truth** for that query. This is essential for testing the retrieval system's accuracy.

**Example Structure:**
```json
[
  {
    "query_text": "a vegan dessert that require minimum time to prepare",
    "documents": [15969, 421673, 329664, 482506, ...]
  }
]
```

## 📈 Experiments and Results (Expériences et Résultats)

All experimental runs and their corresponding outputs are organized under the **`experiments/`** directory.

---

## 📂 `experiments/`

* **Structure** : Contains subfolders for each experimental run (e.g., `exp1`, `exp2`, etc.).
* **Per-Experiment Folder (`expX`)** : Each folder stores the output of a single run defined by a specific configuration.
    * **`config.json`** : The exact **configuration** used for this specific experiment run (ensures reproducibility).
    * **`recipies_samples_emebdding.csv`** : The **generated embeddings** (e.g., a CSV file containing the recipe IDs and the corresponding vector embeddings).
    * **`metrics/`** : A subfolder dedicated to storing the evaluation results for this experiment.

---

### 📊 `experiments/expX/metrics/` (Detailed Metrics / Métriques Détaillées)

This subfolder contains three critical files for analyzing retrieval performance:

| File Name | Purpose (Objectif) | Granularity (Granularité) |
| :--- | :--- | :--- |
| **`retrieval_result.json`** | Stores the **list of retrieved documents** for every query. | Per **Query**, **Top-K value**, **Model**, and **Configuration**. |
| **`retrieval_per_query.json`** | Stores all calculated retrieval metrics (Precision, Recall, etc.). | Per **Query**, **Top-K value**, **Model**, and **Configuration**. |
| **`retrieval_metrics.json`** | Stores the **aggregated metrics** (e.g., Mean Average Precision, Mean Recall). | Per **Top-K value**, **Model**, and **Configuration** (averaged over all queries). |