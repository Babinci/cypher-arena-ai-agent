i want ai agent with mcp server that will be able via  Open WebUI (we can use https://github.com/open-webui/open-webui python package with uv)
to have chat using that mcp server with: 
- my LM Studio models
- with 2 google gemini models:
    - gemini-2.5-pro-preview-03-25 with free tier 5 Request Per Minute 25 req/day   - prefered but respecting rpm- we can make 5 fast and use then use for block time  gemini-2.5-flash-preview-04-17 if needed
    -  gemini-2.5-flash-preview-04-17 10 Request Per Minute 500 req/day


mcp server should have these tools:
- get contrastive mode - get contrasting pairs with ids / paginated responses maybe with query parameters
- rate contrastive mode pairs (in batches)
- create contrastive mode pairs (in batches)
- get news with query parameters (start time, end time, news_type) 
-  insert topics (in batches)
- get topics / paginated responses maybe with query parameters
- change topics (in batches)



mcp server should be implemented in python


package manager: uv (.venv folder)


development worklow:
- activate python environment on cmd with .venv\Scripts\activate


What i need:
- proper docs and endpoints from cypher arena api