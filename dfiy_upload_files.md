# File Upload

> Upload a file (currently only images are supported) for use when sending messages, enabling multimodal understanding of images and text. Supports png, jpg, jpeg, webp, gif formats. Uploaded files are for use by the current end-user only.

## OpenAPI

````yaml en/openapi_completion.json post /files/upload
paths:
  path: /files/upload
  method: post
  servers:
    - url: '{api_base_url}'
      description: >-
        The base URL for the Completion App API. Replace {api_base_url} with the
        actual API base URL provided for your application (e.g., from
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
              description: >-
                API Key authentication. For all API requests, include your API
                Key in the `Authorization` HTTP Header, prefixed with 'Bearer '.
                Example: `Authorization: Bearer {API_KEY}`. **Strongly recommend
                storing your API Key on the server-side, not shared or stored on
                the client-side, to avoid possible API-Key leakage that can lead
                to serious consequences.**
          cookie: {}
    parameters:
      path: {}
      query: {}
      header: {}
      cookie: {}
    body:
      multipart/form-data:
        schemaArray:
          - type: object
            properties:
              file:
                allOf:
                  - type: string
                    format: binary
                    description: >-
                      The file to be uploaded. Supported image types: png, jpg,
                      jpeg, webp, gif.
              user:
                allOf:
                  - type: string
                    description: >-
                      User identifier, defined by the developer's rules, must be
                      unique within the application.
            required: true
            requiredProperties:
              - file
              - user
        examples:
          example:
            value:
              user: <string>
        description: File upload request. Requires multipart/form-data.
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
                    description: ID of the uploaded file.
              name:
                allOf:
                  - type: string
                    description: File name.
              size:
                allOf:
                  - type: integer
                    description: File size (bytes).
              extension:
                allOf:
                  - type: string
                    description: File extension.
              mime_type:
                allOf:
                  - type: string
                    description: File mime-type.
              created_by:
                allOf:
                  - type: string
                    format: uuid
                    description: End-user ID who uploaded the file.
              created_at:
                allOf:
                  - type: integer
                    format: int64
                    description: Creation timestamp (Unix epoch).
                    example: 1577836800
            refIdentifier: '#/components/schemas/FileUploadResponse'
        examples:
          success:
            value:
              id: 72fa9618-8f89-4a37-9b33-7e1178a24a67
              name: example.png
              size: 1024
              extension: png
              mime_type: image/png
              created_by: 6ad1ab0a-73ff-4ac1-b9e4-cdb312f71f13
              created_at: 1577836800
        description: File uploaded successfully.
    '400':
      application/json:
        schemaArray:
          - type: object
            properties:
              status:
                allOf:
                  - &ref_0
                    type: integer
                    description: HTTP status code.
              code:
                allOf:
                  - &ref_1
                    type: string
                    description: Error code specific to the application.
              message:
                allOf:
                  - &ref_2
                    type: string
                    description: A human-readable error message.
            refIdentifier: '#/components/schemas/ErrorResponse'
        examples:
          example:
            value:
              status: 123
              code: <string>
              message: <string>
        description: |-
          Bad Request. Possible error codes:
          - `no_file_uploaded`: A file must be provided.
          - `too_many_files`: Currently only one file is accepted.
          - `unsupported_preview`: The file does not support preview.
          - `unsupported_estimate`: The file does not support estimation.
    '413':
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
        description: '`file_too_large`: The file is too large.'
    '415':
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
        description: >-
          `unsupported_file_type`: Unsupported extension. Currently only
          document files are accepted (Note: description says image types png,
          jpg, etc. are supported for this endpoint, but this error message
          refers to document files. Clarification might be needed from source
          documentation).
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
    '503':
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
        description: |-
          Service Unavailable. Possible error codes:
          - `s3_connection_failed`: Unable to connect to S3 service.
          - `s3_permission_denied`: No permission to upload files to S3.
          - `s3_file_too_large`: File exceeds S3 size limit.
  deprecated: false
  type: path
components:
  schemas: {}

````