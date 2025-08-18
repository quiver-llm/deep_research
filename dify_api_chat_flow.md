# Send Chat Message

> Send a request to the advanced chat application, supporting various file types and workflow events.

## OpenAPI

````yaml en/openapi_chatflow.json post /chat-messages
paths:
  path: /chat-messages
  method: post
  servers:
    - url: '{api_base_url}'
      description: >-
        The base URL for the Advanced Chat App API. Replace {api_base_url} with
        the actual API base URL provided for your application (e.g., from
        props.appDetail.api_base_url).
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
              query:
                allOf:
                  - type: string
                    description: User input/question content.
              inputs:
                allOf:
                  - type: object
                    description: >-
                      Key/value pairs for app variables. For file type
                      variables, value should be an InputFileObject.
                    additionalProperties:
                      oneOf:
                        - type: string
                        - type: number
                        - type: boolean
                        - $ref: '#/components/schemas/InputFileObjectAdvanced'
                    default: {}
              response_mode:
                allOf:
                  - type: string
                    enum:
                      - streaming
                      - blocking
                    default: streaming
                    description: Response mode. Cloudflare timeout is 100s for blocking.
              user:
                allOf:
                  - type: string
                    description: >-
                      User identifier. **Note**: The Service API does not share
                      conversations created by the WebApp. Conversations created
                      through the API are isolated from those created in the
                      WebApp interface.
              conversation_id:
                allOf:
                  - type: string
                    description: Conversation ID to continue.
              files:
                allOf:
                  - type: array
                    items:
                      $ref: '#/components/schemas/InputFileObjectAdvanced'
                    description: >-
                      List of files for Vision-capable models or general file
                      input.
              auto_generate_name:
                allOf:
                  - type: boolean
                    default: true
                    description: Auto-generate conversation title.
            required: true
            refIdentifier: '#/components/schemas/AdvancedChatRequest'
            requiredProperties:
              - query
              - user
        examples:
          streaming_with_file_and_workflow:
            summary: Streaming mode example with image file
            value:
              inputs:
                user_name: Alice
              query: Analyze this document and tell me its sentiment.
              response_mode: streaming
              conversation_id: conv_12345
              user: user_alice
              files:
                - type: document
                  transfer_method: remote_url
                  url: https://example.com/mydoc.pdf
              auto_generate_name: true
        description: Request body to send an advanced chat message.
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              event:
                allOf:
                  - type: string
                    example: message
              task_id:
                allOf:
                  - type: string
                    format: uuid
              id:
                allOf:
                  - type: string
                    format: uuid
                    description: Unique ID of this response event.
              message_id:
                allOf:
                  - type: string
                    format: uuid
              conversation_id:
                allOf:
                  - type: string
                    format: uuid
              mode:
                allOf:
                  - type: string
                    example: chat
              answer:
                allOf:
                  - type: string
              metadata:
                allOf:
                  - $ref: '#/components/schemas/ResponseMetadata'
              created_at:
                allOf:
                  - type: integer
                    format: int64
            description: Response for blocking mode chat.
            refIdentifier: '#/components/schemas/ChatCompletionResponse'
        examples:
          example:
            value:
              event: message
              task_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              message_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              conversation_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
              mode: chat
              answer: <string>
              metadata:
                usage:
                  prompt_tokens: 123
                  prompt_unit_price: <string>
                  prompt_price_unit: <string>
                  prompt_price: <string>
                  completion_tokens: 123
                  completion_unit_price: <string>
                  completion_price_unit: <string>
                  completion_price: <string>
                  total_tokens: 123
                  total_price: <string>
                  currency: <string>
                  latency: 123
                retriever_resources:
                  - position: 123
                    dataset_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
                    dataset_name: <string>
                    document_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
                    document_name: <string>
                    segment_id: 3c90c3cc-0d44-4b50-8888-8dd25736052a
                    score: 123
                    content: <string>
              created_at: 123
        description: >-
          Successful response. The content type and structure depend on the
          `response_mode`.

          - `blocking`: `application/json` with `ChatCompletionResponse`.

          - `streaming`: `text/event-stream` with `ChunkAdvancedChatEvent`
          stream.
      text/event-stream:
        schemaArray:
          - type: string
            description: >-
              A stream of Server-Sent Events. See `ChunkAdvancedChatEvent` for
              structures.
        examples:
          workflow_events_example:
            summary: Example stream including workflow events
            value: >+
              data: {"event": "workflow_started", "task_id": "task_abc",
              "workflow_run_id": "wf_run_1", "data": {"id": "wf_run_1",
              "workflow_id": "wf_def_xyz", "sequence_number": 1, "created_at":
              1705395332}}


              data: {"event": "node_started", "task_id": "task_abc",
              "workflow_run_id": "wf_run_1", "data": {"id": "node_run_1",
              "node_id": "node_start", "node_type": "start", "title": "Start
              Node", "index": 0, "inputs": {}, "created_at": 1705395333}}


              data: {"event": "message", "task_id": "task_abc", "message_id":
              "msg_123", "conversation_id": "conv_123", "answer": "Processing...
              ", "created_at": 1705395334}


              data: {"event": "node_finished", "task_id": "task_abc",
              "workflow_run_id": "wf_run_1", "data": {"id": "node_run_1",
              "node_id": "node_start", "node_type": "start", "title": "Start
              Node", "index": 0, "status": "succeeded", "elapsed_time": 0.5,
              "created_at": 1705395333}}


              data: {"event": "message_end", "task_id": "task_abc",
              "message_id": "msg_123", "conversation_id": "conv_123",
              "metadata": {"usage": {"total_tokens": 10}}}


              data: {"event": "workflow_finished", "task_id": "task_abc",
              "workflow_run_id": "wf_run_1", "data": {"id": "wf_run_1",
              "workflow_id": "wf_def_xyz", "status": "succeeded",
              "elapsed_time": 2.5, "total_tokens": 150, "total_steps": 3,
              "created_at": 1705395332, "finished_at": 1705395335}}

        description: >-
          Successful response. The content type and structure depend on the
          `response_mode`.

          - `blocking`: `application/json` with `ChatCompletionResponse`.

          - `streaming`: `text/event-stream` with `ChunkAdvancedChatEvent`
          stream.
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
        description: Bad Request. Check parameters.
    '404':
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
        description: Conversation not found.
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
    InputFileObjectAdvanced:
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
          description: >-
            Type of the file. 'document' covers TXT, MD, PDF, HTML, XLSX, DOCX,
            CSV, EML, MSG, PPTX, XML, EPUB. 'image' covers JPG, PNG, GIF, WEBP,
            SVG. 'audio' covers MP3, M4A, WAV, WEBM, AMR. 'video' covers MP4,
            MOV, MPEG, MPGA.
        transfer_method:
          type: string
          enum:
            - remote_url
            - local_file
          description: >-
            Transfer method, `remote_url` for file URL / `local_file` for file
            upload
        url:
          type: string
          format: url
          description: File URL (when the transfer method is `remote_url`)
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
      example:
        type: image
        transfer_method: remote_url
        url: https://example.com/image.png
    ResponseMetadata:
      type: object
      properties:
        usage:
          $ref: '#/components/schemas/Usage'
        retriever_resources:
          type: array
          items:
            $ref: '#/components/schemas/RetrieverResource'
    Usage:
      type: object
      properties:
        prompt_tokens:
          type: integer
        prompt_unit_price:
          type: string
        prompt_price_unit:
          type: string
        prompt_price:
          type: string
        completion_tokens:
          type: integer
        completion_unit_price:
          type: string
        completion_price_unit:
          type: string
        completion_price:
          type: string
        total_tokens:
          type: integer
        total_price:
          type: string
        currency:
          type: string
        latency:
          type: number
          format: double
    RetrieverResource:
      type: object
      properties:
        position:
          type: integer
        dataset_id:
          type: string
          format: uuid
        dataset_name:
          type: string
        document_id:
          type: string
          format: uuid
        document_name:
          type: string
        segment_id:
          type: string
          format: uuid
        score:
          type: number
          format: float
        content:
          type: string

````

# Stop Advanced Chat Message Generation

> Stops an advanced chat message generation task. Only supported in streaming mode.

## OpenAPI

````yaml en/openapi_chatflow.json post /chat-messages/{task_id}/stop
paths:
  path: /chat-messages/{task_id}/stop
  method: post
  servers:
    - url: '{api_base_url}'
      description: >-
        The base URL for the Advanced Chat App API. Replace {api_base_url} with
        the actual API base URL provided for your application (e.g., from
        props.appDetail.api_base_url).
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
        task_id:
          schema:
            - type: string
              required: true
              description: Task ID from the streaming chunk.
      query: {}
      header: {}
      cookie: {}
    body:
      application/json:
        schemaArray:
          - type: object
            properties:
              user:
                allOf:
                  - type: string
                    description: >-
                      User identifier, consistent with the send message call.
                      **Note**: The Service API does not share conversations
                      created by the WebApp. Conversations created through the
                      API are isolated from those created in the WebApp
                      interface.
            required: true
            requiredProperties:
              - user
        examples:
          example:
            value:
              user: <string>
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              result:
                allOf:
                  - type: string
                    example: success
        examples:
          example:
            value:
              result: success
        description: Operation successful.
  deprecated: false
  type: path
components:
  schemas: {}

````

# Next Suggested Questions

> Get next questions suggestions for the current message.

## OpenAPI

````yaml en/openapi_chatflow.json get /messages/{message_id}/suggested
paths:
  path: /messages/{message_id}/suggested
  method: get
  servers:
    - url: '{api_base_url}'
      description: >-
        The base URL for the Advanced Chat App API. Replace {api_base_url} with
        the actual API base URL provided for your application (e.g., from
        props.appDetail.api_base_url).
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
        message_id:
          schema:
            - type: string
              required: true
              description: Message ID.
      query:
        user:
          schema:
            - type: string
              required: true
              description: >-
                User identifier. **Note**: The Service API does not share
                conversations created by the WebApp. Conversations created
                through the API are isolated from those created in the WebApp
                interface.
      header: {}
      cookie: {}
    body: {}
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              result:
                allOf:
                  - type: string
                    example: success
              data:
                allOf:
                  - type: array
                    items:
                      type: string
            refIdentifier: '#/components/schemas/SuggestedQuestionsResponse'
        examples:
          example:
            value:
              result: success
              data:
                - <string>
        description: Successfully retrieved suggested questions.
  deprecated: false
  type: path
components:
  schemas: {}

````