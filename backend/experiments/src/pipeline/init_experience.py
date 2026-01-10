from pathlib import Path
import shutil
from typing import Dict


class InitExperience:
    """Initialize directory structure and input artifacts for an experiment."""

    def __init__(self, config: Dict):
        self.experience_id = config["Experiment_id"]
        self.raw_data_table_name = config["raw_data_table_name"]
        self.number_row_analyse = config.get("number_row_analyse", None)
        self.eval_with_llm_or_ground_truth = config.get(
            "eval_with_llm_or_ground_truth", "llm"
        )

        self.config = config

        self.experience_dir = Path(
            config["experiments_dir"].format(experiment_id=self.experience_id)
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
            "embedding_config": config["embedding_config"],
            "data_columns": config["data_columns"],
            "ID_column": config["ID_column"],
        }

        self.llm = {
            "model": config["llm_model"],
            "context_window": config["context_window"],
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "num_docs_per_call": config["number_doc_per_call"],
            "max_retries_llm_calls": config["max_retries_llm_calls"],
            "llm_json_schema": config["llm_json_schema"],
        }

        self.override_flags = {
            "override_raw_data": config.get("override_raw_data", False),
            "override_embeddings": config.get("override_embeddings", False),
            "override_llm_eval": config.get("override_llm_eval", False),
            "override_documents_retrival": config.get(
                "override_documents_retrival", False
            ),
            "override_embedding_eval": config.get("override_embedding_eval", False),
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
            "input_raw_data_file_path": "raw_data",
            "ground_truth_file_path": "eval_data",
            "query_test_file_path": "eval_data",
            "eval_prompt_file_path": "prompts",
        }

        for config_key, target_dir in file_moves.items():
            src = Path(self.config[config_key])
            self._copy_if_exists(src, self.dirs[target_dir])

    def set_file_paths(self):
        self.paths = {
            "config_file_path": self.dirs["config"]
            / Path(self.config["config_file_path"]).name,
            "input_raw_data_file_path": self.dirs["raw_data"]
            / Path(self.config["input_raw_data_file_path"]).name,
            "input_raw_data_cache_file_path": self.config[
                "input_raw_data_cache_file_path"
            ],
            "output_recipes_embedding_file_path": self.dirs["embedding_data"]
            / Path(self.config["output_recipes_embedding_file_path"]).name,
            "ground_truth_file_path": self.dirs["eval_data"]
            / Path(self.config["ground_truth_file_path"]).name,
            "query_test_file_path": self.dirs["eval_data"]
            / Path(self.config["query_test_file_path"]).name,
            "eval_prompt_file_path": self.dirs["prompts"]
            / Path(self.config["eval_prompt_file_path"]).name,
            "eval_llm_ground_truth_file_path": self.dirs["llm_metrics"]
            / Path(self.config["eval_llm_ground_truth_file_path"]).name,
            "input_embedding_cache_file_path": self.config[
                "input_embedding_cache_file_path"
            ],
            "output_topk_model_query_retrieved_documents_file_path": self.dirs[
                "temp_data"
            ]
            / Path(
                self.config["output_topk_model_query_retrieved_documents_file_path"]
            ).name,
            "output_retrived_documents_relevance_file_path": self.dirs["temp_data"]
            / Path(self.config["output_retrived_documents_relevence_file_path"]).name,
            "output_topk_model_query_retrieved_documents_relevance_file_path": self.dirs[
                "embedding_metrics"
            ]
            / Path(
                self.config[
                    "output_topk_model_query_retrieved_documents_relevance_file_path"
                ]
            ).name,
            "output_retrived_documents_metrics_file_path": self.dirs[
                "embedding_metrics"
            ]
            / Path(self.config["output_retrived_documents_metrics_file_path"]).name,
            "output_retrived_documents_aggregated_metrics_file_path": self.dirs[
                "embedding_metrics"
            ]
            / Path(
                self.config["output_retrived_documents_aggregated_metrics_file_path"]
            ).name,
        }

    def main(self):
        """initialization."""
        self.init_directories()
        self.move_files_to_experience()
        self.set_file_paths()
