Lets review taxonomy.py script, there are a few things i want to you try to improve. 

- we prob should create a `Taxonomy` class that help me add/remove/delete categories. and those actions can be formulated as tool which is then passed to agent. 
- the current workflow still have a lot of problems. For example 
  - there is minimal control over taxonomy generation process, how do we control the depth and breath of the taxonomy
  - in merge taxonomy process, can you decompose this into multiple steps? for example, it should be more transparent on what are the merged categories
  - in prune step it should log what are the ones that was prune away
  - and many more 


Please write a full review in REVIEW.md and draw a plan to fix all issues in PLAN.md file