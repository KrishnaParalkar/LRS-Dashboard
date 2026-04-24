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
*   **Query:**
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
*   **UI Settings:**
    *   **Value Column:** `avg_accuracy.value`
    *   **Format Tab:** Decimal Places: `0`, Suffix: `%`.

### B. Accuracy by Department (Bar Chart)
**Goal:** Compare different teams to find who needs more training.
*   **Query:**
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
*   **UI Settings:**
    *   **X Column:** `by_dept`
    *   **Y Column:** `by_dept.avg_accuracy.value`
    *   **Series Tab:** Change label to `Department Accuracy`.

### C. Training Engagement Funnel
**Goal:** See where people drop off in the introductory video.
*   **Query:**
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
*   **UI Settings:**
    *   **Visualization:** Funnel.
    *   **Step Column:** `by_verb`
    *   **Value Column:** `by_verb.doc_count`.

### D. Recent Activity Log (Table)
**Goal:** A searchable list of the latest employee actions.
*   **Query:**
    ```json
    {
        "index": "statements",
        "sort": [{ "timestamp": "desc" }],
        "size": 100
    }
    ```
*   **UI Settings:**
    *   **Visualization:** Table.
    *   **Columns:** Hide `id`, `_index`, and `authority` for a cleaner look. Enable "Allow Search".

---

## 4. Useful Filter Snippets
*   **Filter by Course:** `"query": { "term": { "context.extensions.https://example.ai/context/course_id.keyword": "SEC-AWARE-01" } }`
*   **Filter by Role:** `"query": { "term": { "context.extensions.https://example.ai/context/role.keyword": "Surgeon" } }`
