# Parts and board ordering

Use **V1 for the existing boat's inspection and repair**. Use **V2 as the developing vehicle-node design**. Neither package is a new-board manufacturing release. V1 retains known electrical defects from the original hardware; V2 still needs final electrical, layout, firmware and assembly validation. The handheld's voice, text, location, display and controls need a separate hardware BOM.

## Pick the right files

| Task | V1 existing board | V2 vehicle-node draft |
|---|---|---|
| Review every PCB item | [BOM review](../../hardware/manufacturing/v1/bom_review.csv) | [BOM review](../../hardware/manufacturing/v2/bom_review.csv) |
| Resolve parts held out of ordering | [Held parts](../../hardware/manufacturing/v1/holds.csv) | [Held parts](../../hardware/manufacturing/v2/holds.csv) |
| Get a quote for candidate parts, one board | [One-board CSV](../../hardware/manufacturing/v1/distributor_candidates_1board.csv) | [One-board CSV](../../hardware/manufacturing/v2/distributor_candidates_1board.csv) |
| Get a quote for candidate parts, five boards | [Fleet-five CSV](../../hardware/manufacturing/v1/distributor_candidates_fleet5.csv) | [Fleet-five CSV](../../hardware/manufacturing/v2/distributor_candidates_fleet5.csv) |
| Quote another selected board count | [Selected-count CSV](../../hardware/manufacturing/v1/distributor_candidates_selected.csv) | [Selected-count CSV](../../hardware/manufacturing/v2/distributor_candidates_selected.csv) |
| Complete the system beyond the PCB | [External parts decisions](../../hardware/manufacturing/v1/external_parts_review.csv) | [External parts decisions](../../hardware/manufacturing/v2/external_parts_review.csv) |
| Assemble or inspect | [V1 assembly guide](ASSEMBLY_V1.md) | [V2 assembly guide](ASSEMBLY_V2.md) |

**Candidate-order CSVs are partial lists.** They omit held selections, optional populations awaiting a decision, and bare PCB features. `CANDIDATE` means the source has a manufacturer and MPN and no specific hold in this review. It does not mean the part was checked against today's catalogue, approved for the footprint, or purchased. Full quantities and omissions are visible in the BOM review and [run manifest](../../hardware/manufacturing/run_manifest.json).

The initial packet reconciles 44 V1 footprints (20 candidate components, 18 held components, 6 bare features) and 118 V2 footprints (90 candidate components, 17 held components, 11 bare features). The V2 BOM's `TOTAL` row is excluded. These counts are by reference, not by distinct part number. Fresh generated counts are in each `summary.json` and the manifest.

## Import a candidate list

1. Choose the board version and quantity. Read its held-parts file before treating the import as a complete shopping list.
2. Upload the CSV to a distributor's list/quote tool. Map `Manufacturer Part Number` to the manufacturer part field, `Quantity` to quantity, and `Customer Reference` to your reference field. Preserve punctuation in part numbers such as `CMS06(TE12L,Q,M)` and `PESD5V0S1BA,115`; the CSV quotes these correctly.
3. Review every matched manufacturer, ordering suffix, package, temperature grade and packaging unit. Resolve alternatives against the electrical requirement and footprint before selecting them. A search suggestion is not an approved substitute.
4. Record the supplier SKU, current stock, unit price, MOQ/reel constraints, chosen quantity and quote date in a saved supplier quote. Confirm the actual supplied count, especially for strips/reels. No current price or availability is promised by this packet.
5. Add the approved held/optional parts and external hardware to the quote. Keep the final accepted quote with the release record before checkout.

Mouser's [Price and Availability Assistant](https://www.mouser.com/en/price-availability/) accepts CSVs with manufacturer part numbers and quantities. DigiKey provides [My Lists](https://www.digikey.com/en/mylists), with [Customer Reference column mapping](https://www.digikey.com/en/blog/q-a-from-digi-keys-list-management-webinar). These tools were checked on 2026-09-17; no account, cart or order was created.

## Quantities and population decisions

The exporter always provides one-board and five-board quantities. Select another quantity with:

```powershell
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/manufacturing/prepare_release.py --boards 3
```

`selected` means the latest `--boards` value in the manifest. Fleet-five always means five identical boards of that version. It does not include a handheld, spare boards, attrition, reusable tools, vehicles or shipping. No spare percentage is added silently.

V2 has two source-described population options: the on-board 5 V converter and the LSE clock. Their reference groups are recorded in [procurement policy](../../hardware/manufacturing/procurement_policy.json). An omitted optional group must be reviewed as a circuit, including its effect on firmware and power sources. The generated source BOM currently counts all components; the ordering helper holds these choices instead of inventing a DNP decision.

V1 holds include the C23 value/MPN conflict, tentative passives/ferrites and source lifecycle concerns. V2 holds include ordering-suffix confirmation, connector mechanical checks and population decisions. None has been silently substituted.

## Bare PCB and assembled-board quotes

There is no fabrication-order ZIP in this packet. Use the review package to prepare a quote conversation, then export manufacturing files only from a frozen, reviewed CAD revision.

Before a board order, record the approved board revision, stack-up/material, thickness, copper weights, finish, solder mask, electrical test, outline and drill source, fabrication tolerances and quantity. Do not infer a stack-up or drill certification from a board render. V1's drill reconstruction is inferred from v5 pad evidence; it is not a recovered original v5 drill file.

For assembled boards, additionally freeze the population/DNP list, exact orderable MPNs, supplier substitutions, stencil/paste requirements and assembler-specific centroid rotation/origin convention. The supplied `positions_review.csv` uses raw KiCad rotations and top-view coordinates; it is **not a production pick-and-place file**. Have the assembler confirm orientation against the annotated pad maps and exact package drawings.

The [procurement handoff](PROCUREMENT_HANDOFF.md) lists the concrete release checks and the reproducible commands. No purchase, quote submission or fabrication order has been placed.
