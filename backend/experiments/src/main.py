import json
import os

from shared.snowflake.client import SnowflakeClient

from experiments.src.pipeline.init_experience import InitExperience
from experiments.src.pipeline.calculate_embedding import CalculateEmbedding
from experiments.src.pipeline.eval_llm_judge import EvalLLMJudge
from experiments.src.pipeline.eval_embedding_models import (
    EvalEmbeddingModels,
)


if __name__ == "__main__":
    # go to the directory experiments
    os.chdir("experiments")

    config_file_path = "config/config.json"

    with open(config_file_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    Experience = InitExperience(config)
    Experience.main()

    # calculate_embedding = CalculateEmbedding(
    #     client=SnowflakeClient(),
    #     raw_data_table_name=Experience.raw_data_table_name,
    #     number_row_analyse=Experience.number_row_analyse,
    #     raw_data_file_path=Experience.paths["input_raw_data_file_path"],
    #     raw_data_cache_file_path=Experience.paths["input_raw_data_cache_file_path"],
    #     embedding_data_file_path=Experience.paths["output_recipes_embedding_file_path"],
    #     embedding_cache_file_path=Experience.paths["input_embedding_cache_file_path"],
    #     data_columns=Experience.embedding_models["data_columns"],
    #     embedding_config=Experience.embedding_models["embedding_config"],
    #     id_column=Experience.embedding_models["ID_column"],
    #     embedding_model_list=Experience.embedding_models["embedding_models"],
    #     override_raw_data=Experience.override_flags["override_raw_data"],
    #     override_embeddings=Experience.override_flags["override_embeddings"],
    # )

    # calculate_embedding.main()

    if "llm" in Experience.eval_with_llm_or_ground_truth.lower():
        eval_llm_judge = EvalLLMJudge(
            client=SnowflakeClient(),
            raw_data_file_path=Experience.paths["input_raw_data_file_path"],
            query_test_file_path=Experience.paths["ground_truth_file_path"],
            prompt_file_path=Experience.paths["eval_prompt_file_path"],
            llm_model=Experience.llm["model"],
            llm_model_context_windows=Experience.llm["context_window"],
            llm_model_max_output_token=Experience.llm["max_tokens"],
            llm_model_temperature=Experience.llm["temperature"],
            number_doc_per_call=Experience.llm["num_docs_per_call"],
            llm_json_schema=Experience.llm["llm_json_schema"],
            eval_llm_ground_truth_file_path=Experience.paths[
                "eval_llm_ground_truth_file_path"
            ],
            override_llm_eval=Experience.override_flags["override_llm_eval"],
        )

        eval_llm_judge.main()

    # eval_embedding_models_with_llm = EvalEmbeddingModels(
    #     client=SnowflakeClient(),
    #     embedding_data_file_path=Experience.paths["output_recipes_embedding_file_path"],
    #     data_columns=Experience.embedding_models["data_columns"],
    #     id_column=Experience.embedding_models["ID_column"],
    #     eval_query_test_file_path=Experience.paths["query_test_file_path"],
    #     ground_truth_file_path=Experience.paths["ground_truth_file_path"],
    #     eval_with_llm_or_ground_truth=Experience.eval_with_llm_or_ground_truth,
    #     embedding_model_list=Experience.embedding_models["embedding_models"],
    #     prompt_file_path=Experience.paths["eval_prompt_file_path"],
    #     llm_model=Experience.llm["model"],
    #     llm_model_context_windows=Experience.llm["context_window"],
    #     llm_model_max_output_token=Experience.llm["max_tokens"],
    #     llm_model_temperature=Experience.llm["temperature"],
    #     llm_json_schema=Experience.llm["llm_json_schema"],
    #     number_doc_per_call=Experience.llm["num_docs_per_call"],
    #     max_retries_llm_calls=Experience.llm["max_retries_llm_calls"],
    #     top_k=Experience.embedding_models["top_k"],
    #     output_retrived_documents_file_path=Experience.paths[
    #         "output_topk_model_query_retrieved_documents_file_path"
    #     ],
    #     output_retrived_documents_relevance_file_path=Experience.paths[
    #         "output_retrived_documents_relevance_file_path"
    #     ],
    #     output_topk_model_query_retrieved_documents_relevance_file_path=Experience.paths[
    #         "output_topk_model_query_retrieved_documents_relevance_file_path"
    #     ],
    #     output_retrived_documents_metrics_file_path=Experience.paths[
    #         "output_retrived_documents_metrics_file_path"
    #     ],
    #     output_retrived_documents_aggregated_metrics_file_path=Experience.paths[
    #         "output_retrived_documents_aggregated_metrics_file_path"
    #     ],
    #     override_documents_retrival=Experience.override_flags[
    #         "override_documents_retrival"
    #     ],
    #     override_embedding_eval=Experience.override_flags["override_embedding_eval"],
    # )

    # eval_embedding_models_with_llm.main()
