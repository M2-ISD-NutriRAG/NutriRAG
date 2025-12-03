CREATE OR REPLACE PROCEDURE create_demo_agent(
  search_desc VARCHAR,
  transform_desc VARCHAR,
  agent_instr VARCHAR,
  orch_instr VARCHAR
)
RETURNS VARCHAR
LANGUAGE JAVASCRIPT
AS
'
  var spec = `models:
  orchestration: auto
instructions:
  response: "${AGENT_INSTR}"
  orchestration: "${ORCH_INSTR}"
orchestration:
  budget:
      seconds: 300
tools:
  - tool_spec:
      type: generic
      name: serach
      description: "${SEARCH_DESC}"
      input_schema:
        type: object
        properties:
          query:
            type: string
        required:
          - query
  - tool_spec:
      type: generic
      name: transfrom
      description: "${TRANSFORM_DESC}"
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
  serach:
    type: procedure
    name: "SEARCH_RECIPE_DEMO(VARCHAR)"
    identifier: "NUTRIRAG_PROJECT.SERVICES.SEARCH_RECIPE_DEMO"
    execution_environment:
      type: warehouse
      warehouse: SIMPLE_WH
      query_timeout: 60
  transfrom:
    type: procedure
    name: "TRANSFORM_RECIPE_DEMO(NUMBER, VARCHAR)"
    identifier: "NUTRIRAG_PROJECT.SERVICES.TRANSFORM_RECIPE_DEMO"
    execution_environment:
      type: warehouse
      warehouse: SIMPLE_WH
      query_timeout: 60`;
  
  var sql = "CREATE OR REPLACE AGENT demo_agent_test FROM SPECIFICATION $$" + spec + "$$";
  
  snowflake.execute({sqlText: sql});
  
  return "Agent created successfully";
';

-- call to create the agent



CALL create_demo_agent(
  'The test search_recipe_demo function should be called whenever the user expresses an intention to search for a recipe',
  'The transform_recipe_demo function should be called whenever the user asks to modify, adapt, optimize, or transform an existing recipe',
  'Tu es un agent test qui peut appeler deux custom tools.',
  'choose the right tools based on user input.'
);
