# Editorial atlas design

The agreed scope is the landing page and sources page. The audience remains
heritage professionals, researchers and prospective funders. The pages should
introduce the three existing maps and make evidence quality easy to inspect.
The explorer interfaces and scientific payloads are outside this design change.

## Visual brief

The palette is white `#FFFFFF`, slate `#202D3A`, blue `#244FA3`, cool gray
`#EEF2F6` and muted gray `#596875`. Source Serif 4 carries headlines and long-form
reading; IBM Plex Sans carries navigation, captions and source headings. Fonts
are served locally with SIL Open Font License files and asset provenance.

All prose is left aligned. Reading columns stay below about 80 characters.
Sentence case and restrained hierarchy replace decorative labels. The single
visual focus is an actual source-point plate in Equal Earth projection.

Two layout concepts were considered:

```text
Selected: atlas opening + editorial entries
[ identity                         maps / sources / repository ]
[ research title and introduction | actual POI distribution    ]
[                                 | explanatory caption       ]
[ scope       map purpose and limitations        open explorer ]
[ scope       map purpose and limitations        open explorer ]
[ scope       map purpose and limitations        open explorer ]
[ interpretation note             research needs              ]

Alternative: article + three thumbnail panels
[ identity and navigation                                      ]
[ introduction                                                 ]
[ Africa thumbnail | national thumbnail | event thumbnail       ]
[ methods and limitations                                      ]
```

The alternative repeats the earlier identical-panel structure and gives three
unequal kinds of evidence the same treatment. The selected structure uses a
continental plate for orientation and distinct descriptions for the inventory,
national screening and local event inquiry. It avoids implying a required
sequence or ranking between the maps.

The sources page uses a sticky section index on desktop and an in-flow index
on small screens. Its reading order is interpretation, inventory, models,
observations, scenarios, publication scope and provenance. Source attributions,
product identities, scientific limits and withheld-material notes are retained.

## Plate provenance and regeneration

Run from the repository root with the existing local research environment:

```sh
.venv/bin/python scripts/build_atlas_plate.py
.venv/bin/python scripts/check_pages.py
```

The generator reads the unchanged `data/pois/africa_pois.geojson`. It plots all
source points without acquiring data or carrying out exposure analysis. The
source country's `ZA` code controls blue membership; other records are slate.
The caption explicitly describes uneven source coverage. No coastline,
municipal boundary, flood extent or imagery is introduced into the plate.

`docs/assets/institution-atlas-provenance.json` records the source ID/checksum,
projection, display transform, code checksum/commit, environment versions and
SVG checksum. The source snapshot is registered in `metadata/datasets.csv`;
its original acquisition date remains unknown. Regeneration after an inventory
change requires reviewing caption counts, source registration and the displayed
coverage. Do not infer completeness from the visual distribution.

## Review

Desktop browser review checked the composition, locally served typefaces,
readability, section navigation and the three map destinations. The landing
and sources pages fit a 375-pixel content viewport without horizontal overflow.
Keyboard focus and reduced-motion styles are explicit. Site links, SVG point
counts, frame placement, asset checksums, metadata CSV structure and patch
whitespace are checked separately. Remote deployment is outside this change.
