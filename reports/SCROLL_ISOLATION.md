# Scroll isolation verification

The original document grew to 2,417px at 1366×768; the page itself scrolled while the sidebar and explorer also scrolled without boundary containment. The explorer used a fixed height and its left and right panels could pass wheel motion to the document. Asset production status was in a closed disclosure.

The sidebar provider and content inset now fit the dynamic viewport. The sidebar navigation, page content, explorer folder pane and Radix file viewport each own their scroll position and use CSS overscroll containment. The explorer uses a viewport-relative bounded height. Mobile keeps the existing horizontal folder navigation. Keyboard focus is available on both explorer scroll regions. Production status and its backend-driven checklist are always expanded.

`node scripts/scroll-isolation-qa.mjs` passed against a disposable episode. The read-only response fixture supplied 80 folders and 80 files so each tested pane had real overflow. The script checks mouse-wheel movement and both boundaries of each explorer pane, sidebar movement and boundaries, page movement without sibling movement, Page Down in the file pane, status visibility after refresh, and layouts at 1920×1080, 1440×900, 1366×768, 1024×768 and 390×844. Screenshots are in `artifacts/scroll-isolation/`. A before-state browser inspection recorded actual dimensions; no before screenshot was saved.

`node scripts/asset-explorer-qa.mjs` passed folder navigation, search/sorting, list/grid, preview, upload/download, removal cancellation, responsive layout and axe checks. Dashboard build and 12 frontend tests passed. Physical trackpad, touch hardware and scrollbar dragging were not separately exercised; implementation uses native scrolling without wheel interception.
