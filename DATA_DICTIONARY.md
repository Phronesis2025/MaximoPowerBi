# Data Dictionary

Synthetic IBM Maximo extract. **All data is fabricated.** 23 tables.

| Table | Role | Rows | Cols | Key |
|---|---|--:|--:|---|
| `WORKORDER` | FACT (primary) | 40,688 | 43 | `WONUM` |
| `WOSTATUS` | Fact | 190,001 | 7 | `WOSTATUSID` |
| `LABTRANS` | Fact | 61,315 | 15 | `LABTRANSID` |
| `MATUSETRANS` | Fact | 46,471 | 13 | `MATUSETRANSID` |
| `FAILUREREPORT` | Fact | 12,757 | 11 | `WONUM` |
| `DOWNTIMEREPORT` | Fact | 6,854 | 11 | `ASSETNUM + WONUM + DOWNTIMESTART` |
| `METERREADING` | Fact | 28,005 | 9 | `ASSETNUM + METERNAME + READINGDATE` |
| `INVENTORY` | Fact (snapshot) | 72 | 15 | `ITEMNUM + LOCATION + SITEID` |
| `ASSET` | Dimension | 900 | 24 | `ASSETNUM` |
| `LOCATIONS` | Dimension | 111 | 11 | `LOCATION` |
| `PM` | Dimension | 725 | 18 | `PMNUM` |
| `JOBPLAN` | Dimension | 24 | 8 | `JPNUM` |
| `JOBTASK` | Reference | 74 | 5 | `JPNUM + JPTASKID` |
| `ASSETMETER` | Reference | 388 | 8 | `ASSETNUM + METERNAME + SITEID` |
| `LABOR` | Dimension | 80 | 9 | `LABORCODE` |
| `PERSON` | Dimension | 80 | 7 | `PERSONID` |
| `CRAFT` | Dimension | 12 | 6 | `CRAFT` |
| `ITEM` | Dimension | 24 | 8 | `ITEMNUM` |
| `COMPANIES` | Dimension | 18 | 7 | `COMPANY` |
| `FAILURECODE` | Dimension | 148 | 5 | `FAILURECODE` |
| `SITE` | Reference | 3 | 6 | `SITEID` |
| `ORGANIZATION` | Reference | 1 | 6 | `ORGID` |
| `DIM_DATE` | Dimension | 1,461 | 14 | `DATE` |

---

## `WORKORDER`

**Role:** FACT (primary) &nbsp;&nbsp; **Rows:** 40,688 &nbsp;&nbsp; **Key:** `WONUM`

One row per work order. The central fact table. STATUS=CAN must be excluded from most KPIs.

| Column | Example |
|---|---|
| `WONUM` | `1013563` |
| `DESCRIPTION` | `Weekly operator round` |
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `WOCLASS` | `WORKORDER` |
| `WORKTYPE` | `PM` |
| `STATUS` | `CLOSE` |
| `STATUSDATE` | `2025-01-13 16:07:00` |
| `ASSETNUM` | `BOILER-00571` |
| `LOCATION` | `HOUSTON-UTILITIES-03` |
| `PARENT` | *(blank)* |
| `PMNUM` | `PM-00454` |
| `JPNUM` | `JP-HOU-005` |
| `WOPRIORITY` | `3` |
| `REPORTDATE` | `2024-12-29 08:38:00` |
| `REPORTEDBY` | `L00048` |
| `TARGSTARTDATE` | `2024-12-29 06:00:00` |
| `TARGCOMPDATE` | `2025-01-01 07:30:00` |
| `SCHEDSTART` | `2024-12-29 12:12:00` |
| `SCHEDFINISH` | `2024-12-30 15:12:00` |
| `ACTSTART` | `2024-12-31 14:45:00` |
| `ACTFINISH` | `2024-12-31 15:00:00` |
| `ESTDUR` | `0.47` |
| `ESTLABHRS` | `0.47` |
| `ESTLABCOST` | `22.09` |
| `ESTMATCOST` | `6.67` |
| `ACTLABHRS` | `0.40` |
| `ACTLABCOST` | `17.97` |
| `ACTMATCOST` | `0.00` |
| `ACTTOOLCOST` | `0.00` |
| `ACTSERVCOST` | `0.00` |
| `DOWNTIME` | `0.00` |
| `FAILURECODE` | *(blank)* |
| `PROBLEMCODE` | *(blank)* |
| `SUPERVISOR` | `L00031` |
| `LEAD` | `L00032` |
| `CREWID` | `CREW-HOU-2` |
| `OWNERGROUP` | `MAINT-HOU` |
| `GLACCOUNT` | `6400-HOU-102` |
| `ISTASK` | `0` |
| `HISTORYFLAG` | `1` |
| `CHANGEBY` | `MAXADMIN` |
| `CHANGEDATE` | `2025-01-13 12:52:00` |

## `WOSTATUS`

**Role:** Fact &nbsp;&nbsp; **Rows:** 190,001 &nbsp;&nbsp; **Key:** `WOSTATUSID`

One row per work order status change. Use for cycle-time and status-duration analysis.

| Column | Example |
|---|---|
| `WOSTATUSID` | `63334` |
| `WONUM` | `1013711` |
| `SITEID` | `HOUSTON` |
| `STATUS` | `APPR` |
| `CHANGEDATE` | `2024-11-07 16:12:00` |
| `CHANGEBY` | `MAXADMIN` |
| `MEMO` | `Approved for scheduling` |

## `LABTRANS`

**Role:** Fact &nbsp;&nbsp; **Rows:** 61,315 &nbsp;&nbsp; **Key:** `LABTRANSID`

One row per labor transaction. Sums to WORKORDER.ACTLABCOST.

| Column | Example |
|---|---|
| `LABTRANSID` | `20439` |
| `WONUM` | `1020967` |
| `SITEID` | `AURORA` |
| `ORGID` | `MAINCO` |
| `LABORCODE` | `L00067` |
| `CRAFT` | `OPER` |
| `TRANSDATE` | `2024-06-16 14:00:00` |
| `STARTDATE` | `2024-06-16 12:38:00` |
| `FINISHDATE` | `2024-06-16 08:00:00` |
| `REGULARHRS` | `0.22` |
| `PREMIUMPAYHOURS` | `0.19` |
| `PAYRATE` | `41.36` |
| `LINECOST` | `20.89` |
| `TRANSTYPE` | `WORK` |
| `TASKID` | *(blank)* |

## `MATUSETRANS`

**Role:** Fact &nbsp;&nbsp; **Rows:** 46,471 &nbsp;&nbsp; **Key:** `MATUSETRANSID`

One row per material issue. Sums to WORKORDER.ACTMATCOST.

| Column | Example |
|---|---|
| `MATUSETRANSID` | `15491` |
| `WONUM` | `1020220` |
| `SITEID` | `AURORA` |
| `ORGID` | `MAINCO` |
| `ITEMNUM` | `ITM-0009` |
| `ITEMSETID` | `ITEMSET1` |
| `LOCATION` | `AURORA-STORE` |
| `BINNUM` | `BIN-013` |
| `QUANTITY` | `1` |
| `UNITCOST` | `678.17` |
| `LINECOST` | `678.17` |
| `TRANSDATE` | `2025-12-28 13:45:00` |
| `ISSUETYPE` | `ISSUE` |

## `FAILUREREPORT`

**Role:** Fact &nbsp;&nbsp; **Rows:** 12,757 &nbsp;&nbsp; **Key:** `WONUM`

One row per reported failure. Drives MTBF and bad-actor analysis.

| Column | Example |
|---|---|
| `WONUM` | `1028338` |
| `ASSETNUM` | `VALVE-00549` |
| `LOCATION` | `HOUSTON-LAB-01` |
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `FAILURECODE` | `FC-VALVE` |
| `PROBLEMCODE` | `PACKING-LEAK` |
| `CAUSECODE` | `PACKING-WEAR` |
| `REMEDYCODE` | `REPACK` |
| `TYPE` | `ASSET` |
| `REPORTDATE` | `2024-04-16 13:52:00` |

## `DOWNTIMEREPORT`

**Role:** Fact &nbsp;&nbsp; **Rows:** 6,854 &nbsp;&nbsp; **Key:** `ASSETNUM + WONUM + DOWNTIMESTART`

One row per downtime event. Elapsed wall-clock hours, NOT labor hours.

| Column | Example |
|---|---|
| `ASSETNUM` | `BOILER-00635` |
| `WONUM` | `1028430` |
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `DOWNTIMESTART` | `2024-06-17 06:30:00` |
| `DOWNTIMEEND` | `2024-06-18 17:30:00` |
| `DOWNTIME` | `16.48` |
| `TYPE` | `OPERATIONAL` |
| `REPORTDATE` | `2024-05-30 15:07:00` |
| `REPORTEDBY` | `L00047` |
| `PROBLEMCODE` | `ALARM` |

## `METERREADING`

**Role:** Fact &nbsp;&nbsp; **Rows:** 28,005 &nbsp;&nbsp; **Key:** `ASSETNUM + METERNAME + READINGDATE`

One row per asset per meter per reading date. Condition-monitoring trend.

| Column | Example |
|---|---|
| `ASSETNUM` | `AHU-00300` |
| `SITEID` | `BEDFORD` |
| `METERNAME` | `PRESSURE` |
| `READINGDATE` | `2024-10-12 17:23:00` |
| `READING` | `85.9` |
| `NEWREADING` | `85.9` |
| `MEASUREUNITID` | `PSI` |
| `READINGTYPE` | `ACTUAL` |
| `INSPECTOR` | `L00023` |

## `INVENTORY`

**Role:** Fact (snapshot) &nbsp;&nbsp; **Rows:** 72 &nbsp;&nbsp; **Key:** `ITEMNUM + LOCATION + SITEID`

One row per item per storeroom. Current balances, not history.

| Column | Example |
|---|---|
| `ITEMNUM` | `ITM-0001` |
| `LOCATION` | `HOUSTON-STORE` |
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `ITEMSETID` | `ITEMSET1` |
| `CURBAL` | `12` |
| `MINLEVEL` | `6` |
| `MAXLEVEL` | `24` |
| `REORDERPOINT` | `6` |
| `AVGCOST` | `331.71` |
| `STDCOST` | `340.00` |
| `ISSUEUNIT` | `EA` |
| `ABCTYPE` | `B` |
| `ISSUEYTD` | `50` |
| `LASTISSUEDATE` | `2026-02-14` |

## `ASSET`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 900 &nbsp;&nbsp; **Key:** `ASSETNUM`

One row per asset. Self-referencing hierarchy via PARENT. CRITICALITY 1=highest.

| Column | Example |
|---|---|
| `ASSETNUM` | `AHU-00301` |
| `DESCRIPTION` | `Air Handling Unit 00301` |
| `SITEID` | `BEDFORD` |
| `ORGID` | `MAINCO` |
| `LOCATION` | `BEDFORD-WAREHOUSE-03` |
| `PARENT` | *(blank)* |
| `STATUS` | `OPERATING` |
| `ASSETTYPE` | `AHU` |
| `ITEMNUM` | *(blank)* |
| `SERIALNUM` | `SN70398250` |
| `MANUFACTURER` | `VALVMFG` |
| `VENDOR` | `HVACPRO` |
| `INSTALLDATE` | `2015-06-29` |
| `PURCHASEPRICE` | `34242.26` |
| `REPLACECOST` | `40405.87` |
| `TOTDOWNTIME` | `0.00` |
| `TOTALCOST` | `0.00` |
| `YTDCOST` | `0.00` |
| `PRIORITY` | `4` |
| `CRITICALITY` | `4` |
| `ISRUNNING` | `1` |
| `CLASSSTRUCTUREID` | `CS-AHU` |
| `CHANGEDATE` | `2015-06-29 10:07:00` |
| `CHANGEBY` | `MAXADMIN` |

## `LOCATIONS`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 111 &nbsp;&nbsp; **Key:** `LOCATION`

One row per location. Self-referencing hierarchy via PARENT. TYPE distinguishes OPERATING from STOREROOM/REPAIR/SALVAGE.

| Column | Example |
|---|---|
| `LOCATION` | `HOUSTON-PLANT` |
| `DESCRIPTION` | `Houston Process Facility - Site Root` |
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `TYPE` | `OPERATING` |
| `STATUS` | `OPERATING` |
| `PARENT` | *(blank)* |
| `GLACCOUNT` | `6000-HOU-000` |
| `ISRUNNING` | `1` |
| `CHANGEDATE` | `2023-07-01 14:45:00` |
| `CHANGEBY` | `MAXADMIN` |

## `PM`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 725 &nbsp;&nbsp; **Key:** `PMNUM`

One row per PM schedule. Drives PM work order generation.

| Column | Example |
|---|---|
| `PMNUM` | `PM-00242` |
| `DESCRIPTION` | `Semi-annual electrical inspection` |
| `SITEID` | `BEDFORD` |
| `ORGID` | `MAINCO` |
| `ASSETNUM` | `PANEL-00291` |
| `LOCATION` | `BEDFORD-STAMPING-02` |
| `JPNUM` | `JP-BED-003` |
| `FREQUENCY` | `6` |
| `FREQUNIT` | `MONTHS` |
| `NEXTDATE` | *(blank)* |
| `LASTSTARTDATE` | *(blank)* |
| `LASTCOMPDATE` | *(blank)* |
| `STATUS` | `ACTIVE` |
| `PRIORITY` | `3` |
| `LEADTIME` | `5` |
| `WOSTATUS` | `APPR` |
| `USEFREQUENCY` | `1` |
| `ROUTE` | *(blank)* |

## `JOBPLAN`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 24 &nbsp;&nbsp; **Key:** `JPNUM`

One row per job plan.

| Column | Example |
|---|---|
| `JPNUM` | `JP-AUR-003` |
| `DESCRIPTION` | `Semi-annual electrical inspection` |
| `SITEID` | `AURORA` |
| `ORGID` | `MAINCO` |
| `STATUS` | `ACTIVE` |
| `JPDURATION` | `4.00` |
| `TEMPLATETYPE` | `ITEM` |
| `PRIMARYCRAFT` | `ELECT` |

## `JOBTASK`

**Role:** Reference &nbsp;&nbsp; **Rows:** 74 &nbsp;&nbsp; **Key:** `JPNUM + JPTASKID`

One row per job plan task.

| Column | Example |
|---|---|
| `JPNUM` | `JP-BED-003` |
| `SITEID` | `BEDFORD` |
| `JPTASKID` | `40` |
| `DESCRIPTION` | `Clean and restore to service` |
| `ESTDUR` | `1.00` |

## `ASSETMETER`

**Role:** Reference &nbsp;&nbsp; **Rows:** 388 &nbsp;&nbsp; **Key:** `ASSETNUM + METERNAME + SITEID`

One row per asset per meter.

| Column | Example |
|---|---|
| `ASSETNUM` | `PUMP-00307` |
| `SITEID` | `BEDFORD` |
| `METERNAME` | `VIBRATION` |
| `MEASUREUNITID` | `IN/S` |
| `LASTREADING` | *(blank)* |
| `LASTREADINGDATE` | *(blank)* |
| `ACTIVE` | `1` |
| `METERTYPE` | `GAUGE` |

## `LABOR`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 80 &nbsp;&nbsp; **Key:** `LABORCODE`

One row per labor record. Primary CRAFT flattened from LABORCRAFTRATE.

| Column | Example |
|---|---|
| `LABORCODE` | `L00027` |
| `PERSONID` | `P00027` |
| `DISPLAYNAME` | `Kofi Delacroix` |
| `CRAFT` | `MILLWR` |
| `SITEID` | `BEDFORD` |
| `ORGID` | `MAINCO` |
| `STATUS` | `ACTIVE` |
| `HIREDATE` | `2015-10-19` |
| `PAYRATE` | `49.97` |

## `PERSON`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 80 &nbsp;&nbsp; **Key:** `PERSONID`

One row per person.

| Column | Example |
|---|---|
| `PERSONID` | `P00027` |
| `DISPLAYNAME` | `Kofi Delacroix` |
| `FIRSTNAME` | `Kofi` |
| `LASTNAME` | `Delacroix` |
| `STATUS` | `ACTIVE` |
| `LOCATIONSITE` | `BEDFORD` |
| `PRIMARYEMAIL` | `kdelacroix@example.invalid` |

## `CRAFT`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 12 &nbsp;&nbsp; **Key:** `CRAFT`

One row per craft. Rate flattened from CRAFTRATE.

| Column | Example |
|---|---|
| `CRAFT` | `MILLWR` |
| `DESCRIPTION` | `Millwright` |
| `ORGID` | `MAINCO` |
| `STDRATE` | `47.50` |
| `PREMIUMRATE` | `71.25` |
| `ACTIVE` | `1` |

## `ITEM`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 24 &nbsp;&nbsp; **Key:** `ITEMNUM`

One row per item master record.

| Column | Example |
|---|---|
| `ITEMNUM` | `ITM-0009` |
| `DESCRIPTION` | `Pressure transmitter 0-100psi` |
| `ITEMSETID` | `ITEMSET1` |
| `ISSUEUNIT` | `EA` |
| `ORDERUNIT` | `EA` |
| `ROTATING` | `0` |
| `COMMODITYGROUP` | `INSTRUMENTS` |
| `STATUS` | `ACTIVE` |

## `COMPANIES`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 18 &nbsp;&nbsp; **Key:** `COMPANY`

Vendors/manufacturers/couriers. TYPE V=vendor M=manufacturer C=courier.

| Column | Example |
|---|---|
| `COMPANY` | `APEXCAL` |
| `NAME` | `Apex Calibration Services` |
| `TYPE` | `C` |
| `ORGID` | `MAINCO` |
| `COMPANYSETID` | `COMPSET1` |
| `PAYMENTTERMS` | `Net 45` |
| `ACTIVE` | `1` |

## `FAILURECODE`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 148 &nbsp;&nbsp; **Key:** `FAILURECODE`

Failure taxonomy. PARENT links PROBLEM/CAUSE/REMEDY codes to a failure class.

| Column | Example |
|---|---|
| `FAILURECODE` | `HIGH-DP` |
| `DESCRIPTION` | `High Dp` |
| `ORGID` | `MAINCO` |
| `PARENT` | `FC-AHU` |
| `TYPE` | `PROBLEM` |

## `SITE`

**Role:** Reference &nbsp;&nbsp; **Rows:** 3 &nbsp;&nbsp; **Key:** `SITEID`

One row per site. Maximo is multi-site by design.

| Column | Example |
|---|---|
| `SITEID` | `HOUSTON` |
| `ORGID` | `MAINCO` |
| `DESCRIPTION` | `Houston Process Facility` |
| `ACTIVE` | `1` |
| `CITY` | `Houston` |
| `STATE` | `TX` |

## `ORGANIZATION`

**Role:** Reference &nbsp;&nbsp; **Rows:** 1 &nbsp;&nbsp; **Key:** `ORGID`

One row per organization.

| Column | Example |
|---|---|
| `ORGID` | `MAINCO` |
| `DESCRIPTION` | `Maintenance Holdings Inc` |
| `BASECURRENCY1` | `USD` |
| `ITEMSETID` | `ITEMSET1` |
| `COMPANYSETID` | `COMPSET1` |
| `ACTIVE` | `1` |

## `DIM_DATE`

**Role:** Dimension &nbsp;&nbsp; **Rows:** 1,461 &nbsp;&nbsp; **Key:** `DATE`

One row per calendar day. NOT a Maximo table - added for the model. Fiscal year starts 1 October.

| Column | Example |
|---|---|
| `DATE` | `2024-05-02` |
| `YEAR` | `2024` |
| `QUARTER` | `Q2` |
| `MONTHNUM` | `5` |
| `MONTHSHORT` | `May` |
| `YEARMONTH` | `2024-05` |
| `MONTHYEARLABEL` | `May 2024` |
| `ISOWEEK` | `18` |
| `DAYOFWEEK` | `4` |
| `DAYSHORT` | `Thu` |
| `ISWEEKEND` | `0` |
| `FISCALYEAR` | `2024` |
| `FISCALPERIOD` | `8` |
| `ISPASTORTODAY` | `1` |

