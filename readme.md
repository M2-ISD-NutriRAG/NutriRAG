# 🚀 Project Name

## 📝 Overview

This project is structured to manage a machine learning pipeline focused on generating and evaluating data embeddings for clustering and retrieval tasks. It uses configuration files to define the embedding models and data columns, ensuring reproducible experimentation.

---

## 📂 Project Structure Hierarchy

The following diagram illustrates the project's file and folder organization:

## ⚙️ Configuration Files

The **`config/`** directory houses the critical configuration logic for the machine learning pipeline.

### `config/col_embedding_model.json`

* **Location**: `config/col_embedding_model.json`
* **Purpose**: This JSON file is the single source of truth for defining which data columns (`col`) are targeted for embedding generation and which specific embedding models (`embedding_model`) should be used for the transformation.
* **Role in Pipeline**: Ensures that experiments involving different columns and models are strictly defined and tracked.

---

## 💾 Data Storage

The **`data/`** directory manages both the raw input data and the resulting processed embeddings.

### `data/data.csv`

* **Content**: The main dataset used for analysis.
* **Volume**: Contains **1,000 data points**.

### `data/embeddings/`

* **Content**: Storage for all generated vector embeddings.
* **Generation Source**: These embeddings are created based on the specifications detailed in `config/col_embedding_model.json`.

---

## 📊 Metrics and Evaluation

The **`metrics/`** directory is dedicated to storing the results and performance evaluations of the models.

### `metrics/clustering/`

* **Content**: Stores all **clustering metrics** (e.g., Silhouette Score, Inertia, etc.).
* **Granularity**: Each file or subdirectory here tracks the clustering performance for a specific combination of:
    * **Configuration** defined in `col_embedding_model.json`.
    * **Embedding Model** used.

### `metrics/retrieval/`

* **Content**: Stores all **retrieval metrics** (e.g., Mean Average Precision (MAP), Recall@K).
* **Granularity**: Each file tracks the retrieval performance for a specific combination of:
    * **Configuration** defined in `col_embedding_model.json`.
    * **Embedding Model** used.

---

## Environment and Utility Files

These files are essential for setting up the environment, tracking dependencies, and managing sensitive information.

### 🔒 `.env` File (Environment Variables)

This file stores sensitive credentials and project parameters. **It MUST be added to `.gitignore`.**

| Variable Name | Description | Default Value |
| :--- | :--- | :--- |
| `USER` | Database User Name | |
| `PASSWORD` | Database Password | |
| `PASSCODE` | MFA Passcode (if required) | |
| `ACCOUNT` | Database Account Identifier | |
| `WAREHOUSE` | Database Warehouse Name | |
| `DATABASE` | Database Name | |
| `SCHEMA` | Database Schema Name | |
| `TABLE` | Database Table Name | |
| `CONFIG_FILE_PATH` | Path to the main configuration file | `"config/col_embedding_model.json"` |
| `EXPERIENCE_ID` | Identifier for tracking experimental runs | `1` |

### 📚 Other Utility Files

| File | Purpose |
| :--- | :--- |
| **`.gitignore`** | Specifies files and folders (e.g., `.env`, `data/embeddings/`) that should not be committed to Git. |
| **`requirements.txt`** | Lists all necessary Python package dependencies required to run the project. |
| **`notebooks/`** | Contains Jupyter Notebooks (`.ipynb`) for data exploration, experimentation, and interactive analysis. |

---

## 🚀 Getting Started

1.  Clone the repository: `git clone <repo-url>`
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create the `.env` file with the required credentials.
4.  Begin experimentation using the notebooks in `notebooks/`.

Would you like me to generate the contents of the `.env` file for easy copying?