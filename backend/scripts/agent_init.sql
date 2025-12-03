CREATE OR REPLACE AGENT demo_agent_test FROM SPECIFICATION $$
models:
  orchestration: auto
instructions:
  response: "You are a helpful assistant that helps users find and modify recipes based on their preferences and dietary needs."
  orchestration: "Choose the right tools based on user input, and plan your actions carefully to achieve the best results for the user."
orchestration:
  budget:
    seconds: 300
tools:
  - tool_spec:
      type: generic
      name: search
      description: "The search_recipe_demo function should be called whenever the user expresses an intention to search for a recipe"
      input_schema:
        type: object
        properties:
          query:
            type: string
        required:
          - query
  - tool_spec:
      type: generic
      name: transform
      description: "The transform_recipe_demo function should be called whenever the user asks to modify, adapt, optimize, or transform an existing recipe"
      input_schema:
        type: object
        properties:
          goal:
            type: string
          recipe_id:
            type: number
        required:
          - goal
          - recipe_id
tool_resources:
  search:
    type: procedure
    name: "SEARCH_RECIPE_DEMO(VARCHAR)"
    identifier: "NUTRIRAG_PROJECT.SERVICES.SEARCH_RECIPE_DEMO"
    execution_environment:
      type: warehouse
      warehouse: SIMPLE_WH
      query_timeout: 60
  transform:
    type: procedure
    name: "TRANSFORM_RECIPE_DEMO(NUMBER, VARCHAR)"
    identifier: "NUTRIRAG_PROJECT.SERVICES.TRANSFORM_RECIPE_DEMO"
    execution_environment:
      type: warehouse
      warehouse: SIMPLE_WH
      query_timeout: 60
$$;
