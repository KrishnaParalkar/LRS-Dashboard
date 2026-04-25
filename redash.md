# Redash Dashboard Guide: Learning Analytics

This guide explains how to turn the xAPI data seeded by `seed.py` into professional visualizations in Redash.

## 1. Setup Data Source
1.  Go to **Settings > Data Sources > New Data Source**.
2.  Select **Elasticsearch**.
3.  **Name:** `Ralph LRS`
4.  **Base URL:** `http://elasticsearch:9200`
5.  Save and Test Connection.

---

## 2. The Redash Workflow
To build your dashboard, follow these three steps for every chart:

### Step 1: Create a Query
*   Click **Create** > **Query** in the top navigation bar.
*   Select **Ralph LRS** as your Data Source.
*   Paste your JSON query (see examples below) and click **Execute**.
*   Click **Save** and give the query a clear name.
*   **Pro-Tip:** Click **"Add description"** right below the query name to add context that will appear on your dashboard widgets!

### Step 2: Create a Visualization
*   On the query results page, click **Add Visualization**.
*   Select your **Visualization Type** (Bar, Line, Counter, etc.).
*   **Series Tab:** Use this to rename technical columns (like `by_dept.avg_accuracy.value`) to friendly names like `Accuracy %`.
*   **Format Tab:** Use this to set decimal places to `0` and add `%` as a suffix.
*   **Data Labels Tab:** Check "Show Data Labels" to show numbers directly on the bars.
*   Click **Save**.

### Step 3: Add Widget to Dashboard
*   Click **Create** > **Dashboard** to start a new dashboard.
*   Click **Add Widget**.
*   Search for your Query and select the specific Visualization you just made.
*   **Optional:** Add a **Text Box** widget to write big headers or detailed analysis next to your charts.

---

## 3. Perfected Visualizations (Ready to Copy-Paste)

### A. Overall Success Rate (Counter)
**Goal:** A big hero number showing the company's average score.
*   **Elasticsearch (Ralph LRS) Query:**
    ```json
    {
        "index": "statements",
        "query": { "term": { "verb.display.en-US": "responded" } },
        "aggs": {
            "avg_accuracy": {
                "avg": {
                    "script": "doc['result.success'].size() > 0 ? (doc['result.success'].value ? 100 : 0) : 0"
                }
            }
        },
        "size": 0
    }
    ```
*   **PostgreSQL (SQL LRS) Query:**
    ```sql
    SELECT
      AVG(CASE WHEN payload->'result'->>'success' = 'true' THEN 100.0 ELSE 0.0 END) AS avg_accuracy
    FROM xapi_statement
    WHERE payload->'verb'->'display'->>'en-US' = 'responded'
      AND payload->'result'->'success' IS NOT NULL;
    ```
*   **UI Settings:**
    *   **Value Column:** `avg_accuracy.value` (or `avg_accuracy` for SQL)
    *   **Format Tab:** Decimal Places: `0`, Suffix: `%`.

### B. Accuracy by Department (Bar Chart)
**Goal:** Compare different teams to find who needs more training.
*   **Elasticsearch (Ralph LRS) Query:**
    ```json
    {
        "index": "statements",
        "query": { "term": { "verb.display.en-US": "responded" } },
        "aggs": {
            "by_dept": {
                "terms": { "field": "context.extensions.https://example.ai/context/dept.keyword" },
                "aggs": {
                    "avg_accuracy": {
                        "avg": {
                            "script": "doc['result.success'].size() > 0 ? (doc['result.success'].value ? 100 : 0) : 0"
                        }
                    }
                }
            }
        },
        "size": 0
    }
    ```
*   **PostgreSQL (SQL LRS) Query:**
    ```sql
    SELECT
      payload->'context'->'extensions'->>'https://example.ai/context/dept' AS "By Department",
      AVG(CASE WHEN payload->'result'->>'success' = 'true' THEN 100.0 ELSE 0.0 END) AS "Avg Accuracy"
    FROM xapi_statement
    WHERE payload->'verb'->'display'->>'en-US' = 'responded'
      AND payload->'result'->'success' IS NOT NULL
    GROUP BY 1;
    ```
*   **UI Settings:**
    *   **X Column:** `by_dept`
    *   **Y Column:** `by_dept.avg_accuracy.value` (or `avg_accuracy` for SQL)
    *   **Series Tab:** Change label to `Department Accuracy`.

### C. Training Engagement Funnel
**Goal:** See where people drop off in the introductory video.
*   **Elasticsearch (Ralph LRS) Query:**
    ```json
    {
        "index": "statements",
        "query": { "terms": { "verb.display.en-US": ["played", "completed"] } },
        "aggs": {
            "by_verb": { "terms": { "field": "verb.display.en-US.keyword" } }
        },
        "size": 0
    }
    ```
*   **PostgreSQL (SQL LRS) Query:**
    ```sql
    SELECT
      payload->'verb'->'display'->>'en-US' AS "Verb",
      COUNT(*) AS "Document Count"
    FROM xapi_statement
    WHERE payload->'verb'->'display'->>'en-US' IN ('played', 'completed')
    GROUP BY 1;
    ```
*   **UI Settings:**
    *   **Visualization:** Funnel.
    *   **Step Column:** `by_verb`
    *   **Value Column:** `by_verb.doc_count` (or `doc_count` for SQL).

### D. Recent Activity Log (Table)
**Goal:** A searchable list of the latest employee actions.
*   **Elasticsearch (Ralph LRS) Query:**
    ```json
    {
        "index": "statements",
        "sort": [{ "timestamp": "desc" }],
        "size": 100,
        "_source": [
            "timestamp",
            "actor.name",
            "context.extensions.https://example.ai/context/dept",
            "verb.display.en-US",
            "object.definition.name.en-US",
            "result.response",
            "result.score.scaled",
            "result.success",
            "result.duration"
        ]
    }
    ```
*   **PostgreSQL (SQL LRS) Query:**
    ```sql
    SELECT 
      payload->>'timestamp' AS "Time",
      payload->'actor'->>'name' AS "User",
      payload->'context'->'extensions'->>'https://example.ai/context/dept' AS "Department",
      payload->'verb'->'display'->>'en-US' AS "Action",
      payload->'object'->'definition'->'name'->>'en-US' AS "Activity",
      payload->'result'->>'response' AS "Response",
      payload->'result'->'score'->>'scaled' AS "Score",
      payload->'result'->>'success' AS "Success",
      payload->'result'->>'duration' AS "Duration"
    FROM xapi_statement
    ORDER BY payload->>'timestamp' DESC
    LIMIT 100;
    ```
*   **UI Settings:**
    *   **Visualization:** Table.
    *   **General:** Enable "Allow Search".
    *   **Columns (For Elasticsearch users):** Because we filtered the data in the JSON query, you don't need to manually hide any columns! Just **Rename & Reorder** them:
        1.  `timestamp` ➔ **Time** (Set Data Type to Date/Time)
        2.  `actor.name` ➔ **User**
        3.  `context.extensions.https://example.ai/context/dept` ➔ **Department**
        4.  `verb.display.en-US` ➔ **Action**
        5.  `object.definition.name.en-US` ➔ **Activity**
        6.  `result.response` ➔ **Response**
        7.  `result.score.scaled` ➔ **Score**
        8.  `result.success` ➔ **Success**
        9.  `result.duration` ➔ **Duration**
    *   **Columns (For PostgreSQL users):** The SQL query natively handles aliases, so your columns will automatically be named properly. You only need to set `Time` to Date/Time format.

*   **Pro-Tip: Auto-Rename using SQL (Query Results):**
    If you don't want to rename columns manually in the UI, you can use Redash's "Query Results" feature!
    1. Save the JSON query above and note its ID (e.g., `123` from the URL).
    2. Create a new query, set the Data Source to **Query Results**, and use this SQL:
    ```sql
    SELECT 
      timestamp AS "Time",
      `actor_name` AS "User",
      `context_extensions_https_//example_ai/context/dept` AS "Department",
      `verb_display_en-US` AS "Action",
      `object_definition_name_en-US` AS "Activity",
      `result_response` AS "Response",
      `result_score_scaled` AS "Score",
      `result_success` AS "Success",
      `result_duration` AS "Duration"
    FROM query_123 -- Replace 123 with your actual Query ID
    ```
    3. Save this new SQL query, and when you build your Dashboard, add **this** query's table widget (not the raw JSON one)!

---

## 4. Useful Filter Snippets
*   **Filter by Course:** `"query": { "term": { "context.extensions.https://example.ai/context/course_id.keyword": "SEC-AWARE-01" } }`
*   **Filter by Role:** `"query": { "term": { "context.extensions.https://example.ai/context/role.keyword": "Surgeon" } }`

---

## 5. Alternative: SQL LRS (Direct SQL Querying)
We have also spun up **YetAnalytics SQL LRS** (`lrsql`) running on port `8080`, which stores its xAPI statements in a dedicated PostgreSQL database instead of Elasticsearch.

### Connect Redash to SQL LRS
1. Go to **Settings > Data Sources > New Data Source**.
2. Select **PostgreSQL**.
3. **Name:** `SQL LRS`
4. **Host:** `postgres-lrs`
5. **Port:** `5432`
6. **User:** `lrsql`
7. **Password:** `lrsql_secret`
8. **Database Name:** `lrsql`
9. Save and Test Connection.

### Querying SQL LRS
Instead of writing JSON queries and mapping them with Query Results, you can simply write standard SQL queries against the `statement` table in this new data source!

**Example SQL Query:**
```sql
SELECT
  payload->>'timestamp' AS "Time",
  payload->'actor'->>'name' AS "User",
  payload->'verb'->'display'->>'en-US' AS "Action",
  payload->'object'->'definition'->'name'->>'en-US' AS "Activity"
FROM xapi_statement
ORDER BY payload->>'timestamp' DESC
LIMIT 100;
```
