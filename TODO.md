help me complete the following tasks 

- [] fix the following error, and double check other options to make sure you didn't make similar mistakes
    ```
    > pyalex -d institutions --works-count "100:500"
    2025-07-31 20:36:20,678 - pyalex:50 - DEBUG - Email: 0lh.cheng0@gmail.com
    2025-07-31 20:36:20,678 - pyalex:51 - DEBUG - User Agent: pyalex/0.1.dev156+g8e24548.d20250731
    2025-07-31 20:36:20,678 - pyalex:52 - DEBUG - Debug mode enabled - API URLs and internal details will be displayed
    2025-07-31 20:36:20,679 - pyalex:126 - DEBUG - API URL: https://api.openalex.org/institutions?filter=works_count:100%3A500
    2025-07-31 20:36:20,679 - pyalex:135 - DEBUG - Requesting URL: https://api.openalex.org/institutions?filter=works_count:100%3A500&per-page=25
    2025-07-31 20:36:21,379 - pyalex:109 - DEBUG - Full traceback:
    Traceback (most recent call last):
    File "/fred/oz318/luhanc/pyalex/pyalex/cli/commands/institutions.py", line 178, in institutions
        results = query.get(limit=limit_to_use)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/fred/oz318/luhanc/pyalex/pyalex/entities/base.py", line 229, in get
        resp_list = self._get_from_url(self.url)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/fred/oz318/luhanc/pyalex/pyalex/entities/base.py", line 143, in _get_from_url
        raise QueryError(res.json()["message"])
    pyalex.core.response.QueryError: Value for param works_count must be a number.
    Error: Value for param works_count must be a number.
    ```

- [] currently group_by can only supply the first page. So make sure you only request the first page if `--group-by` is supplied. If you request more than page 1 you will get the following error 
    ```
    {"error":"Pagination error.","message":"Unable to paginate beyond page 1. Group-by is limited to page 1 with up to 200 results at this time."}
    ```

- [] Please scan repository for redundant sync implementation. Note that you can assume all required packages async are installed. The only case where sync implementation is needed is when the first page of a query tells me that there are more than 10000 response items, which means we need cursor paging (while user requested all items). Please remove redundant sync functions. this should help reducing unnecessary code. 