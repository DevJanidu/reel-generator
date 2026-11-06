# Old versus new UI

Both sets were captured from the application against disposable local data. Old screens were captured before frontend changes from the reviewed source snapshot. New examples include synthetic test episodes; differing counts are fixture data, not a comparison of actual production metrics.

|Area|Before|After|
|---|---|---|
|Navigation|Local page state; permanent icon rail on mobile|Page URLs, episode URL state, collapsible Sidebar and mobile Sheet|
|Typography|Frequent 8–13px labels|16px body, readable secondary copy and 28–30px page headings|
|Home|Large decorative hero competing with work|Compact intro, real metrics, recent Reels and next actions|
|Queue|Home section only|Dedicated real-state job table and separate capacities|
|Ideas|Good existing genre and history logic; custom/native confirmation|Preserved logic, official Dialog and consistent cards|
|Activity|Custom drawer|Accessible Sheet plus a dedicated activity route|
|Help|Job-progress reference only|Searchable A–Z Accordion plus original detailed reference|
|Button styling|Strong opaque yellow; legacy styles obscured queue text|Translucent gold actions, transparent Reel links, neutral Help rows|
|Sidebar hover|Adjacent highlights touched|6px separation between items|
|Health|Technical status scattered across pages|Dedicated read-only health overview|
|Exports|Filename/download/current QC and inline confirmation|Same contracts, AlertDialog and on-demand media preview control|

## Screenshots

- [Old desktop Home](evidence/old-home.png)
- [New desktop Home](evidence/new-home.png)
- [Old mobile Home](evidence/old-home-mobile.png)
- [New mobile Home](evidence/new-home-mobile.png)
- [New Ideas](evidence/new-ideas.png)
- [Queue with readable Reel links and separated hover state](evidence/new-queue-hover.png)
- [Neutral Help with an expanded answer](evidence/new-help.png)
- [Populated Script Studio](evidence/new-script.png)
- [Populated Asset Manager](evidence/new-assets.png)

The complete captures for all 15 desktop/mobile routes are in artifacts/new-ui. Populated examples are named *-populated.png. Images contain disposable data, not production stories or credentials.

## Performance evidence

Baseline main JS was approximately 406.58 kB / 125.96 kB gzip. The redesigned application introduces Radix and additional routes; total JS is larger, about 599 kB / 190 kB gzip. It is split into React, primitives, TanStack data and application chunks; the largest is approximately 209 kB. CSS is approximately 138 kB / 25 kB gzip, versus 42 kB / 11 kB gzip initially. Font assets remain local.

Build time is under one second for the Vite bundling step on this machine, excluding TypeScript. No runtime-speed, Lighthouse, LCP or production network benchmark is claimed. Split chunks support caching; they do not by themselves prove a faster initial load.

