# Execute Workflow

> Execute workflow. Cannot be executed without a published workflow.

## OpenAPI

````yaml en/openapi_workflow.json post /workflows/run
paths:
  path: /workflows/run
  method: post
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
      path: {}
      query: {}
      header: {}
      cookie: {}
    body:
      application/json:
        schemaArray:
          - type: object
            properties:
              inputs:
                allOf:
                  - type: object
                    description: >-
                      Key/value pairs for workflow variables. Value for a file
                      array type variable should be a list of
                      InputFileObjectWorkflow.
                    additionalProperties:
                      oneOf:
                        - type: string
                        - type: number
                        - type: boolean
                        - type: object
                        - type: array
                          items:
                            $ref: '#/components/schemas/InputFileObjectWorkflow'
                    example:
                      user_query: Translate this for me.
                      target_language: French
              response_mode:
                allOf:
                  - type: string
                    enum:
                      - streaming
                      - blocking
                    description: Response mode. Cloudflare timeout is 100s for blocking.
              user:
                allOf:
                  - type: string
                    description: User identifier.
            required: true
            refIdentifier: '#/components/schemas/WorkflowExecutionRequest'
            requiredProperties:
              - inputs
              - response_mode
              - user
        examples:
          basic_execution:
            summary: Basic workflow execution
            value:
              inputs:
                query: 'Summarize this text: ...'
              response_mode: streaming
              user: user_workflow_123
          with_file_array_variable:
            summary: Example with a file array input variable
            value:
              inputs:
                my_documents:
                  - type: document
                    transfer_method: local_file
                    upload_file_id: uploaded_file_id_abc
                  - type: image
                    transfer_method: remote_url
                    url: https://example.com/image.jpg
              response_mode: blocking
              user: user_workflow_456
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              workflow_run_id:
                allOf:
                  - type: string
                    format: uuid
              task_id:
                allOf:
                  - type: string
                    format: uuid
              data:
                allOf:
                  - $ref: '#/components/schemas/WorkflowFinishedData'
            description: Response for blocking mode workflow execution.
            refIdentifier: '#/components/schemas/WorkflowCompletionResponse'
        examples:
          example:
            value:
              workflow_run_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              task_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              data:
                id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
                workflow_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
                status: running
                outputs: {}
                error: <string>
                elapsed_time: 123
                total_tokens: 123
                total_steps: 0
                created_at: 123
                finished_at: 123
        description: |-
          Successful workflow execution. Structure depends on `response_mode`.
          - `blocking`: `application/json` with `WorkflowCompletionResponse`.
          - `streaming`: `text/event-stream` with `ChunkWorkflowEvent` stream.
      text/event-stream:
        schemaArray:
          - type: string
            description: >-
              A stream of Server-Sent Events. See `ChunkWorkflowEvent` for
              structures.
        examples:
          example:
            value: <string>
        description: |-
          Successful workflow execution. Structure depends on `response_mode`.
          - `blocking`: `application/json` with `WorkflowCompletionResponse`.
          - `streaming`: `text/event-stream` with `ChunkWorkflowEvent` stream.
    '400':
      application/json:
        schemaArray:
          - type: object
            properties:
              status:
                allOf:
                  - &ref_0
                    type: integer
                    nullable: true
              code:
                allOf:
                  - &ref_1
                    type: string
                    nullable: true
              message:
                allOf:
                  - &ref_2
                    type: string
            refIdentifier: '#/components/schemas/ErrorResponse'
        examples:
          example:
            value:
              status: 123
              code: <string>
              message: <string>
        description: >-
          Bad Request for workflow operation. Possible error codes:
          invalid_param, app_unavailable, provider_not_initialize,
          provider_quota_exceeded, model_currently_not_support,
          workflow_request_error.
    '500':
      application/json:
        schemaArray:
          - type: object
            properties:
              status:
                allOf:
                  - *ref_0
              code:
                allOf:
                  - *ref_1
              message:
                allOf:
                  - *ref_2
            refIdentifier: '#/components/schemas/ErrorResponse'
        examples:
          example:
            value:
              status: 123
              code: <string>
              message: <string>
        description: Internal server error.
  deprecated: false
  type: path
components:
  schemas:
    InputFileObjectWorkflow:
      type: object
      required:
        - type
        - transfer_method
      properties:
        type:
          type: string
          enum:
            - document
            - image
            - audio
            - video
            - custom
          description: Type of file.
        transfer_method:
          type: string
          enum:
            - remote_url
            - local_file
          description: >-
            Transfer method, `remote_url` for image URL / `local_file` for file
            upload
        url:
          type: string
          format: url
          description: Image URL (when the transfer method is `remote_url`)
        upload_file_id:
          type: string
          description: >-
            Uploaded file ID, which must be obtained by uploading through the
            File Upload API in advance (when the transfer method is
            `local_file`)
      anyOf:
        - properties:
            transfer_method:
              enum:
                - remote_url
            url:
              type: string
              format: url
          required:
            - url
          not:
            required:
              - upload_file_id
        - properties:
            transfer_method:
              enum:
                - local_file
            upload_file_id:
              type: string
          required:
            - upload_file_id
          not:
            required:
              - url
    WorkflowFinishedData:
      type: object
      required:
        - id
        - workflow_id
        - status
        - created_at
        - finished_at
      properties:
        id:
          type: string
          format: uuid
        workflow_id:
          type: string
          format: uuid
        status:
          type: string
          enum:
            - running
            - succeeded
            - failed
            - stopped
        outputs:
          type: object
          additionalProperties: true
          nullable: true
        error:
          type: string
          nullable: true
        elapsed_time:
          type: number
          format: float
          nullable: true
        total_tokens:
          type: integer
          nullable: true
        total_steps:
          type: integer
          default: 0
        created_at:
          type: integer
          format: int64
        finished_at:
          type: integer
          format: int64

````