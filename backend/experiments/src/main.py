import json
import os

from shared.snowflake.client import SnowflakeClient

from experiments.src.pipeline.init_experience import InitExperience
from experiments.src.pipeline.calculate_embedding import CalculateEmbedding
from experiments.src.pipeline.eval_llm_judge import EvalLLMJudge
from experiments.src.pipeline.eval_embedding_models import EvalEmbeddingModels


if __name__ == "__main__":
    # go to the directory experiments
    os.chdir("experiments")

    config_file_path = "config/config.json"

    with open(config_file_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    Experience = InitExperience(config)
    Experience.main()

    calculate_embedding = CalculateEmbedding(
        client=SnowflakeClient(),
        raw_data_table_name=Experience.raw_data_table_name,
        raw_data_file_path=Experience.paths["raw_data_file"],
        embedding_data_file_path=Experience.paths["embedding_data_file"],
        embedding_cache_file_path=Experience.paths["input_embedding_cache_file"],
        data_columns_for_embedding=Experience.embedding_models["columns_to_clean"],
        embedding_configuration=Experience.embedding_models["columns_embedding"],
        embedding_model_list=Experience.embedding_models["embedding_models"],
        override_raw_data=Experience.override_flags["override_raw_data"],
        override_embeddings=Experience.override_flags["override_embeddings"],
    )

    calculate_embedding.main()

    eval_llm_judge = EvalLLMJudge(
        client=SnowflakeClient(),
        raw_data_file_path=Experience.paths["raw_data_file"],
        query_test_file_path=Experience.paths["ground_truth_file"],
        prompt_file_path=Experience.paths["eval_prompt_with_justification"],
        llm_model=Experience.llm["model"],
        llm_model_context_windows=Experience.llm["context_window"],
        llm_model_max_output_token=Experience.llm["max_tokens"],
        llm_model_temperature=Experience.llm["temperature"],
        number_doc_per_call=Experience.llm["num_docs_per_call"],
        json_schema=Experience.llm["json_schema_with_justification"],
        eval_llm_ground_truth_file_path=Experience.paths["eval_llm_ground_truth_file"],
        override_llm_eval=Experience.override_flags["override_llm_eval"],
    )

    eval_llm_judge.main()

    evla_embedding_models = EvalEmbeddingModels(
        client=SnowflakeClient(),
        embedding_data_file_path=Experience.paths["embedding_data_file"],
        data_columns=Experience.embedding_models["data_columns"],
        eval_query_test_file_path=Experience.paths["query_test_file"],
        embedding_model_list=Experience.embedding_models["embedding_models"],
        prompt_file_path=Experience.paths["eval_prompt_without_justification"],
        llm_model=Experience.llm["model"],
        llm_model_context_windows=Experience.llm["context_window"],
        llm_model_max_output_token=Experience.llm["max_tokens"],
        llm_model_temperature=Experience.llm["temperature"],
        json_schema=Experience.llm["json_schema_without_justification"],
        number_doc_per_call=Experience.llm["num_docs_per_call"],
        max_retries_llm_calls=Experience.llm["max_retries_llm_calls"],
        top_k=Experience.embedding_models["top_k"],
        output_retrived_documents_file_path=Experience.paths[
            "topk_model_query_retrived_documents_file"
        ],
        output_retrived_query_documents_relevance_file=Experience.paths[
            "retrived_query_documents_relevance_file"
        ],
        output_topk_model_query_retrieved_documents_relevance_file=Experience.paths[
            "output_topk_model_query_retrieved_documents_relevance_file"
        ],
        output_retrived_documents_metrics_file_path=Experience.paths[
            "output_retrived_documents_metrics_file"
        ],
        output_retrived_documents_aggregated_metrics_file_path=Experience.paths[
            "output_retrived_documents_aggregated_metrics_file"
        ],
        override_documents_retrival=Experience.override_flags[
            "override_documents_retrival"
        ],
        override_embedding_eval=Experience.override_flags["override_embedding_eval"],
    )

    evla_embedding_models.main()
