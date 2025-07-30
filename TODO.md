# Fix --all option

it seems current --all can be broken 

```
> pyalex -d funders --country AU --all --json funders.json
2025-07-30 16:59:39,422 - pyalex:77 - DEBUG - Email: 0lh.cheng0@gmail.com
2025-07-30 16:59:39,422 - pyalex:78 - DEBUG - User Agent: pyalex/0.1.dev143+gcd7cd4c.d20250729
2025-07-30 16:59:39,422 - pyalex:79 - DEBUG - Debug mode enabled - API URLs and internal details will be displayed
2025-07-30 16:59:39,423 - pyalex:126 - DEBUG - API URL: https://api.openalex.org/funders?filter=country_code:AU
2025-07-30 16:59:39,423 - pyalex:135 - DEBUG - Requesting URL: https://api.openalex.org/funders?filter=country_code:AU&per-page=200
2025-07-30 16:59:40,709 - pyalex:144 - DEBUG - Response type: <class 'pyalex.core.response.OpenAlexResponseList'>
2025-07-30 16:59:40,709 - pyalex:149 - DEBUG - Response length: 200
2025-07-30 16:59:40,709 - pyalex:156 - DEBUG - Total count from meta: 1,484
```

The above query is suppose to retrieve all 1484 funders, instead the resulting json only contains the results from the first pages

The expected behaviour is for the library to send 8 async queries (1484//200+1), and save all results to funders.json