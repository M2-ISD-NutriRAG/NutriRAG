from pathlib import Path
import shutil
from typing import Dict


class InitExperience:
    """Initialize directory structure and input artifacts for an experiment."""

    def __init__(self, experience_id: str, config: Dict):
        self.experience_id = experience_id
        self.config = config

        self.experience_dir = Path(
            config["experiments_dir"].format(experiment_id=experience_id)
        )

        self.dirs = {
            "config": self.experience_dir / config["config_dir"],
            "raw_data": self.experience_dir / config["raw_data_dir"],
            "embedding_data": self.experience_dir / config["embedding_data_dir"],
            "eval_data": self.experience_dir / config["eval_data_dir"],
            "temp_data": self.experience_dir / config["temp_data_dir"],
            "prompts": self.experience_dir / config["prompts_dir"],
            "metrics": self.experience_dir / config["metrics_dir"],
            "llm_metrics": self.experience_dir / config["llm_metrics_dir"],
            "embedding_metrics": self.experience_dir / config["embedding_metrics_dir"],
        }

        self.embedding_models = {
            "embedding_models": config["embedding_models"],
            "top_k": config["top_k"],
            "columns_to_clean": config["columns_to_clean"],
            "columns_embedding": config["columns_embedding"],
            "data_columns": config["data_columns"],
        }

        self.llm = {
            "model": config["llm_model"],
            "context_window": config["context_window"],
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "num_docs_per_call": config["number_doc_per_call"],
            "max_retries_llm_calls": config["max_retries_llm_calls"],
            "json_schema_with_justification": config[
                "llm_json_format_with_justification"
            ],
            "json_schema_without_justification": config[
                "llm_json_format_without_justification"
            ],
        }

        self.override_flags = {
            "override_raw_data": config.get("override_raw_data", False),
            "override_embeddings": config.get("override_embeddings", False),
            "override_llm_eval": config.get("override_llm_eval", False),
            "override_documents_retrival": config.get(
                "override_documents_retrival", False
            ),
        }

        self.paths = {}

    def init_directories(self):
        self.experience_dir.mkdir(parents=True, exist_ok=True)
        for path in self.dirs.values():
            path.mkdir(parents=True, exist_ok=True)

    def _copy_if_exists(self, src: Path, dst_dir: Path):
        if src.exists():
            shutil.copy2(src, dst_dir)

    def move_files_to_experience(self):
        file_moves = {
            "config_file_path": "config",
            "input_recipies_file": "raw_data",
            "ground_truth_file_path": "eval_data",
            "query_test_file_path": "eval_data",
            "eval_prompt_with_justification_file_path": "prompts",
            "eval_prompt_without_justification_file_path": "prompts",
        }

        for config_key, target_dir in file_moves.items():
            src = Path(self.config[config_key])
            self._copy_if_exists(src, self.dirs[target_dir])

    def set_file_paths(self):
        self.paths = {
            "config_file": self.dirs["config"]
            / Path(self.config["config_file_path"]).name,
            "raw_data_file": self.dirs["raw_data"]
            / Path(self.config["input_recipies_file"]).name,
            "embedding_data_file": self.dirs["embedding_data"]
            / self.config["output_recipies_embedding_file"],
            "ground_truth_file": self.dirs["eval_data"]
            / Path(self.config["ground_truth_file_path"]).name,
            "query_test_file": self.dirs["eval_data"]
            / Path(self.config["query_test_file_path"]).name,
            "eval_prompt_with_justification": self.dirs["prompts"]
            / Path(self.config["eval_prompt_with_justification_file_path"]).name,
            "eval_prompt_without_justification": self.dirs["prompts"]
            / Path(self.config["eval_prompt_without_justification_file_path"]).name,
            "eval_llm_ground_truth_file": self.dirs["llm_metrics"]
            / Path(self.config["eval_llm_ground_truth_file_path"]).name,
            "input_embedding_cache_file": self.config[
                "input_embedding_cache_file_path"
            ],
            "retrived_documents_file": self.dirs["temp_data"]
            / Path(self.config["output_retrieved_documents_file"]).name,
        }

    def main(self):
        """initialization."""
        self.init_directories()
        self.move_files_to_experience()
        self.set_file_paths()
