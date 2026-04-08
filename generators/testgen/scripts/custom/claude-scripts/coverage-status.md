# Coverage Work Status

### Vf

Completed — all custom coverpoints at 100%. Any gaps are bugs.

### Vls (formerly VlsCustom — now merged)

**Note:** VlsCustom has been merged into Vls. The single `Vls.csv` testplan covers all 310 LS instructions with both custom and non-custom coverpoints. Extensions: `Vls8,Vls16,Vls32,Vls64`. When updating `testplans/Vls.csv`, also update `working-testplans/duplicates/Vls-save.csv`.

| Coverpoint                       | Status    | Coverage                                              |
| -------------------------------- | --------- | ----------------------------------------------------- |
| cp_custom_vwholeRegLS_vill       | partial   | Vls8=100%; Vls16/32/64=66.66%                         |
| cp_custom_vwholeRegLS_lmul       | completed | 100%                                                  |
| cp_custom_maskLS                 | completed | 100% (Vls16/32/64); Vls8=0% inherent (SEW>8 required) |
| cp_custom_ls_indexed             | untested  |                                                       |
| cp_custom_ffLS_update_vl         | untested  |                                                       |
| cp_custom_indexed_emul_data_only | untested  |                                                       |
| cp_custom_masked_v0_operand      | untested  |                                                       |
