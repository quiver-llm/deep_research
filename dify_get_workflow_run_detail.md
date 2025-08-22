# Get Workflow Run Detail

> Retrieve the current execution results of a workflow task based on the workflow execution ID.

## OpenAPI

````yaml en/openapi_workflow.json get /workflows/run/{workflow_run_id}
paths:
  path: /workflows/run/{workflow_run_id}
  method: get
  servers:
    - url: '{api_base_url}'
      description: >-
        The base URL for the Workflow App API. Replace {api_base_url} with the
        actual API base URL.
      variables:
        api_base_url:
          type: string
          description: Actual base URL of the API
          default: https://api.dify.ai/v1
  request:
    security:
      - title: ApiKeyAuth
        parameters:
          query: {}
          header:
            Authorization:
              type: http
              scheme: bearer
              description: API Key authentication.
          cookie: {}
    parameters:
      path:
        workflow_run_id:
          schema:
            - type: string
              required: true
              description: >-
                Workflow Run ID, can be obtained from workflow execution
                response or streaming events.
              format: uuid
      query: {}
      header: {}
      cookie: {}
    body: {}
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              id:
                allOf:
                  - type: string
                    format: uuid
              workflow_id:
                allOf:
                  - type: string
                    format: uuid
              status:
                allOf:
                  - type: string
                    enum:
                      - running
                      - succeeded
                      - failed
                      - stopped
              inputs:
                allOf:
                  - type: string
                    description: JSON string of input content.
              outputs:
                allOf:
                  - type: object
                    additionalProperties: true
                    nullable: true
                    description: JSON object of output content.
              error:
                allOf:
                  - type: string
                    nullable: true
              total_steps:
                allOf:
                  - type: integer
              total_tokens:
                allOf:
                  - type: integer
              created_at:
                allOf:
                  - type: integer
                    format: int64
              finished_at:
                allOf:
                  - type: integer
                    format: int64
                    nullable: true
              elapsed_time:
                allOf:
                  - type: number
                    format: float
                    nullable: true
            refIdentifier: '#/components/schemas/WorkflowRunDetailResponse'
        examples:
          example:
            value:
              id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              workflow_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              status: running
              inputs: <string>
              outputs: {}
              error: <string>
              total_steps: 123
              total_tokens: 123
              created_at: 123
              finished_at: 123
              elapsed_time: 123
        description: Successfully retrieved workflow run details.
    '404':
      _mintlify/placeholder:
        schemaArray:
          - type: any
            description: Workflow run not found.
        examples: {}
        description: Workflow run not found.
  deprecated: false
  type: path
components:
  schemas: {}

````