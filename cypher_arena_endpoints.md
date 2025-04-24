# AI Agent API Documentation

**Base URL:** `https://backend.cypher-arena.com/words/agent/`

---

## 1. Contrast Pairs

Endpoints for managing and retrieving contrastive pairs.

### 1.1 Get Contrast Pairs

Retrieve a paginated list of contrast pairs.

- **Method:** `GET`
- **URL:** `/contrast-pairs/`
- **Query Parameters:**
  - `page` (integer, optional): Page number for pagination.
  - `count` (integer, optional): Number of items per page (default: 10, max: 100).
- **Success Response (200 OK):**
  ```json
  {
    "total": 150,            // Total number of pairs across all pages
    "page": 1,               // Current page number
    "count": 10,             // Number of items on the current page
    "next": "/words/agent/contrast-pairs/?page=2&count=10", // URL for next page (or null)
    "previous": null,        // URL for previous page (or null)
    "results": [
      {
        "id": 1,
        "item1": "apple",
        "item2": "orange",
        "tags": [],          // List of associated tags (currently not populated by agent endpoints)
        "ratings": []        // List of associated ratings (currently not populated by agent endpoints)
      }
      // ... more pairs
    ]
  }
  ```

### 1.2 Batch Create Contrast Pairs

Create multiple contrast pairs in a single request.

- **Method:** `POST`
- **URL:** `/contrast-pairs/`
- **Request Body:**
  ```json
  {
    "pairs": [
      {"item1": "string", "item2": "string"},
      {"item1": "string", "item2": "string"}
      // ... more pairs
    ]
  }
  ```
- **Success Response (201 Created):**
  - Returns a list of the newly created contrast pairs in the same format as the `results` array in the GET request.
  ```json
  [
    {
      "id": 101,
      "item1": "sun",
      "item2": "moon",
      "tags": [],
      "ratings": []
    },
    {
      "id": 102,
      "item1": "day",
      "item2": "night",
      "tags": [],
      "ratings": []
    }
  ]
  ```
- **Error Response (400 Bad Request):**
  - If input data is invalid or a database error occurs.
  ```json
  {
    "pairs": [
      {
        "item2": ["This field is required."]
      },
      {}
    ]
  }
  // OR
  {
      "error": "Failed to create pairs: [database error message]"
  }
  ```

### 1.3 Batch Rate Contrast Pairs

Rate multiple contrast pairs in a single request. A user fingerprint is automatically generated based on the request headers (User-Agent, IP) to associate the rating.

- **Method:** `POST`
- **URL:** `/contrast-pairs/rate/`
- **Request Body:**
  ```json
  {
    "ratings": [
      {"pair_id": integer, "rating": integer (1-5)},
      {"pair_id": integer, "rating": integer (1-5)}
      // ... more ratings
    ]
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "status": "batch rating successful",
    "updated_count": 2 // Number of pairs successfully rated/updated
  }
  ```
- **Error Response (400 Bad Request):**
  - If input data is invalid (e.g., missing fields, invalid rating value), a pair ID doesn't exist, or a database error occurs during the transaction. Even if some ratings succeed, a 400 is returned if any fail.
  ```json
  {
    "ratings": [
      {
        "rating": ["Ensure this value is less than or equal to 5."]
      },
      {}
    ]
  }
  // OR
  {
    "errors": [
      "ContrastPair with id 999 does not exist."
    ],
    "updated_count": 1 // Number successfully updated before the error
  }
  // OR
  {
      "error": "Failed to rate pairs: [database error message]"
  }
  ```

---

## 2. News

Endpoints for retrieving news records, typically sourced from external processes (like Perplexity research).

### 2.1 Get News

Retrieve news records filtered by a required date range and optional news type.

- **Method:** `GET`
- **URL:** `/news/`
- **Query Parameters:**
  - `start_time` (string, **required**): Start datetime in ISO 8601 format (e.g., `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`).
  - `end_time` (string, **required**): End datetime in ISO 8601 format.
  - `news_type` (string, optional): Filter by news category (e.g., `general_news`, `polish_showbiznes`, `sport`, `tech`, `science`, `politics`). See `CypherArenaPerplexityDeepResearch.news_source` model field for possible values.
- **Success Response (200 OK):**
  - Returns a list of news records matching the filters.
  ```json
  [
    {
      "id": 1,
      "data_response": { ... }, // Original JSON response from the source
      "start_date": "2025-04-22T17:36:07.966519Z",
      "end_date": "2025-04-23T17:36:07.966519Z",
      "search_type": "sonar-pro", // e.g., Model used for search
      "news_source": "tech"
    }
    // ... more news records
  ]
  ```
- **Error Response (400 Bad Request):**
  - If required parameters (`start_time`, `end_time`) are missing or datetime format is invalid.
  ```json
  {
    "error": "'start_time' and 'end_time' query parameters are required."
  }
  // OR
  {
    "error": "Invalid datetime format. Please use ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ)."
  }
  ```

---

## 3. Topics

Endpoints for managing topics (represented by the `Temator` model).

### 3.1 Get Topics

Retrieve a paginated list of topics, with optional filtering by source.

- **Method:** `GET`
- **URL:** `/topics/`
- **Query Parameters:**
  - `page` (integer, optional): Page number for pagination.
  - `count` (integer, optional): Number of items per page (default: 10, max: 100).
  - `source` (string, optional): Filter topics by their source field.
- **Success Response (200 OK):**
  ```json
  {
    "total": 50,             // Total number of topics matching filter (if any)
    "page": 1,
    "count": 10,
    "next": "/words/agent/topics/?page=2&count=10",
    "previous": null,
    "results": [
      {
        "id": 1,
        "name": "Technology",
        "source": "manual"
      },
      {
        "id": 2,
        "name": "Science",
        "source": "generated"
      }
      // ... more topics
    ]
  }
  ```

### 3.2 Batch Insert Topics

Insert multiple topics in a single request. Uses `get_or_create` based on the `name` field to avoid creating duplicate topics. If a topic with the same name already exists, it will be included in the response, but its `source` will not be updated.

- **Method:** `POST`
- **URL:** `/topics/`
- **Request Body:**
  ```json
  {
    "topics": [
      {"name": "string", "source": "string (optional, default: 'agent')"},
      {"name": "string"} // Source defaults to 'agent'
      // ... more topics
    ]
  }
  ```
- **Success Response (201 Created):**
  - Returns a list of the topics that were either newly created or already existed (matched by name).
  ```json
  [
    {
      "id": 10,
      "name": "History",
      "source": "manual"
    },
    {
      "id": 11,
      "name": "Geography",
      "source": "agent"
    }
  ]
  ```
- **Error Response (400 Bad Request):**
  - If input data is invalid (e.g., missing `name`) or a database error occurs.
  ```json
  {
    "topics": [
      {
        "name": ["This field is required."]
      },
      {}
    ]
  }
  // OR
  {
      "error": "Failed to create topics: [database error message]"
  }
  ```

### 3.3 Batch Update Topics

Update multiple existing topics in a single request. Each item in the `updates` list must contain the `id` of the topic to update and at least one field (`name` or `source`) to modify.

- **Method:** `PATCH`
- **URL:** `/topics/`
- **Request Body:**
  ```json
  {
    "updates": [
      {"id": integer, "name": "string (optional)", "source": "string (optional)"},
      {"id": integer, "source": "string (optional)"}
      // ... more updates
    ]
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "status": "batch update successful",
    "updated_count": 2, // Number of topics successfully updated
    "updated_ids": [1, 5] // List of IDs of the updated topics
  }
  ```
- **Error Response (400 Bad Request):**
  - If input data is invalid (e.g., missing `id`, no update fields provided), a topic ID doesn't exist, or a database error occurs. Even if some updates succeed, a 400 is returned if any fail.
  ```json
  {
    "updates": [
      {
        "id": ["This field is required."]
      },
      {
        "non_field_errors": ["At least one field ('name' or 'source') must be provided for update."]
      }
    ]
  }
  // OR
  {
    "errors": [
      "Temator with id 999 does not exist."
    ],
    "updated_count": 1, // Number successfully updated before the error
    "updated_ids": [1]  // IDs updated before the error
  }
  // OR
  {
      "error": "Failed to update topics: [database error message]"
  }
  ```
