# NHTSA public vehicle data

Inventory of public NHTSA datasets that matter for Glovebox. Every claim is tagged.

- **Documented.** A NHTSA page or file says it. The link is the citation.
- **Observed.** We called the endpoint on 2026-11-22 and recorded the response. The paced run and its counts are in [spikes/2026-11-22-probe.json](spikes/2026-11-22-probe.json). Method and limits are in [rate-limits-and-terms.md](rate-limits-and-terms.md).
- **Unknown.** We could not verify it. Do not build on it until someone checks.

The catalog page for most of this is [NHTSA Datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis). vPIC has its own site.

## What belongs in v1

| Source | Access | v1 |
| --- | --- | --- |
| vPIC VIN decode | Live JSON API, plus an optional Postgres download | Yes. Live decode is the default. |
| Recalls | Live JSON API, plus daily flat files | Yes. Live API, shaped. |
| Complaints | Live JSON API, plus a large daily flat file | Yes, as a summary. Not raw narratives. |
| NCAP 5-star ratings | Live JSON API | Yes. |
| Defect investigations | Daily flat file only. No documented REST API. | Yes, from the 4 MB zip, loaded locally. |
| Manufacturer communications (TSBs and related) | Flat files only. No documented REST API. | No. Later, as an offline index. |
| Products enumeration (`/products/vehicle/...`) | Live JSON, but the year list is not usable | Use only as a hint. Do not trust it as complete. |
| FARS and the Crash API | Live API for fatal crashes from 2010, plus bulk files | No. Different question, easy to misuse. |
| CISS, CRSS, and older crash samples | Bulk files | No. |
| Canadian vehicle specifications | One vPIC endpoint | No. A niche dimension database. |
| Equipment plant codes, Parts 565/566 letters | vPIC endpoints | No. Not a consumer vehicle profile. |
| Fuel economy | Not an NHTSA API. DOE and EPA publish [fueleconomy.gov](https://www.fueleconomy.gov/) | Out of scope. |

## 1. vPIC

The NHTSA Product Information Catalog and Vehicle Listing decodes VINs from what manufacturers submit under 49 CFR Part 565 and related parts. The about page says it is the catalog for VIN decoding, the Manufacturer Information Database, and equipment plant codes, and that it is intended for model years 1981 and forward. Vehicles before the 1981 VIN standard are not decoded. ([About vPIC](https://vpic.nhtsa.dot.gov/about/))

The API home page says the same dataset is what manufacturers submit through the 565 process, and that applications are subject to an automated traffic control. It does not publish a number. ([Vehicle API](https://vpic.nhtsa.dot.gov/api/))

### Coverage, in NHTSA's words

From the [API FAQ](https://vpic.nhtsa.dot.gov/api/Home/Index/FAQ):

- No license and no registration. The API is a free open-data service.
- They state there is no daily cap, ask large batches to run at night US Eastern time or on weekends, and say weekday capacity is about 1000 to 2000 transactions per minute and that they have not hit an upper limit. The downloads page contradicts the "no quota" reading. See the rate-limit note.
- Decode confidence, as they state it: about 99 percent for model year 1995 forward for most brands, about 60 to 65 percent for 1980 to 1994, and no data before 1980 because there was no US VIN standard.
- Foreign vehicles appear only if the manufacturer registered them for import, sale, or use in the United States.
- They aim for 99 percent availability from 6 AM to 6 PM US Eastern, with maintenance usually on weekends. The API is described as up 24 hours otherwise.

Those confidence percentages are NHTSA's own estimates, not something this research remeasured.

### Output formats

Documented on the API page, and observed:

| format | Observed Content-Type | Notes |
| --- | --- | --- |
| omitted | `application/xml` | Default. A decode of the documented partial VIN returned XML. |
| `json` | `application/json` | What the agent should request. |
| `csv` | `application/octet-stream` | A decode returned a one-row CSV. Header names were lowercase. |

The wrapper for JSON and XML is `Count`, `Message`, `SearchCriteria`, `Results`.

The decode `Message` we observed says, in substance, that a missing decoded value means NHTSA does not have data for that variable, and must not be read as evidence that the feature is absent. That sentence has to be part of every decode tool result. It is the difference between a faithful answer and a hallucinated "this car has no side airbags."

### Decode endpoints

Base: `https://vpic.nhtsa.dot.gov/api`

The documented partial VIN used below is the one printed on the API page: `5UXWX7C5*BA` with `modelyear=2011`. ([Vehicle API](https://vpic.nhtsa.dot.gov/api/))

| Method and path | What it is | Observed on 2026-11-22 |
| --- | --- | --- |
| `GET /vehicles/DecodeVin/{vin}` | Key/value rows: `Variable`, `VariableId`, `Value`, `ValueId`. | 200. 12,226 bytes. `Count` 141 for the partial BMW example. |
| `GET /vehicles/DecodeVinValues/{vin}` | One flat object. This is the one to call. | 200. 3,994 bytes. 154 keys, 38 non-empty, 116 empty. ErrorCode `6` (incomplete VIN). Decoded as 2011 BMW X3, xDrive35i. |
| `GET /vehicles/DecodeVinExtended/{vin}` | Pair format plus extra variables. | 200. 12,577 bytes. `Count` 145. |
| `GET /vehicles/DecodeVinValuesExtended/{vin}` | Flat format plus extra variables. | 200. 4,069 bytes. Same 154 keys. 41 non-empty. The extras on this VIN were NCSA body, make, and model. |
| `POST /vehicles/DecodeVINValuesBatch/` | Form fields `format` and `data`. Data shape: `vin,modelYear;vin,modelYear`. Documented maximum 50 VINs. | 200 for two documented partial VINs. 7,924 bytes. `Count` 2. The 50 cap was not stress-tested. |

Documented behavior worth keeping:

- Send `modelyear` when you know it. The page says decoding can target the current year or older, pre-1980, ranges, and recommends always sending the year.
- Partial VINs are allowed. `*` stands in for unknown characters. The 9th character is not required for a partial decode.
- Paths on the HTML page are shown in mixed case. Lowercase links also work. `GetMakesForManufacturer` (plural Makes) is not a route: it returned 404. The documented path is `GetMakeForManufacturer`.

Observed error codes, all with HTTP 200. The caller must read `ErrorCode`. A 200 is not a successful decode.

| Input | ErrorCode | ErrorText we recorded |
| --- | --- | --- |
| `5UXWX7C5*BA` | `6` | `6 - Incomplete VIN` |
| `3GNDA13D76S000000` (an example from the [language samples](https://vpic.nhtsa.dot.gov/api/Home/Index/LanguageExamples)) | `1` | `1 - Check Digit (9th position) does not calculate properly` |
| `5XYKT3A12CG000000` (same page) | `1` | same check-digit text |
| `ABC` | `6,7,11` | incomplete VIN; manufacturer is not registered with NHTSA for sale or importation in the US; position 10 is not a valid model year code (the text lists I, O, Q, U, Z, 0) |
| `3GNDA13D76S00000I` | `1,400` | check digit; `400 - Invalid Characters Present`. `AdditionalErrorText` was `Invalid character(s): 17:I.` `SuggestedVIN` replaced `I` with `!`. |

We did not capture an `ErrorCode` of `0` in this run. A full official list of codes was not found as its own page. The strings above are the API's own text, not a spec we verified beyond these inputs.

Other observed decode facts for the partial BMW:

- Make `BMW`, Model `X3`, ModelYear `2011`, Trim `xDrive35i`, BodyClass SUV/MPV, 3.0 L, 6 cylinders, AWD, 4 doors, plant Munich, Germany.
- Several keys that do not apply to an SUV were the string `Not Applicable` rather than empty: bus floor, bus type, motorcycle chassis and suspension, trailer body and type. Dropping only empty strings still wastes context. The shaper should also drop `Not Applicable`.
- Flat extended added NCSA fields and little else on this VIN. Default to `DecodeVinValues`, not the extended call, unless a caller asks for the NCSA mapping.

### Other vPIC routes

Paths below are the ones printed on the [API page](https://vpic.nhtsa.dot.gov/api/) or linked from it. All were called with `format=json` unless noted.

| Path | Documented role | Observed |
| --- | --- | --- |
| `GET /vehicles/DecodeWMI/{wmi}` | WMI of 3 characters (positions 1 to 3) or 6 (positions 1 to 3 and 12 to 14). | `1FD` returned 200, one row, Ford, incomplete vehicle. The prose example `1T9131` returned 200 with `Count` 0. One empty example does not prove 6-character WMIs are broken. |
| `GET /vehicles/GetWMIsForManufacturer/{nameOrId}` | WMIs for a manufacturer. Name is a LIKE match. Optional `vehicleType`. | `hon` returned 200, `Count` 106, 21,691 bytes. First rows were Honda motorcycle WMIs. No paging parameter is documented for this route. |
| `GET /vehicles/GetAllMakes` | Every make. | 200, `Count` 12440, 615,656 bytes. Too large to hand to a model. |
| `GET /vehicles/GetMakeForManufacturer/{nameOrId}` | Makes for one manufacturer. | `honda` returned 200, 16 rows, make id 474 is HONDA. |
| `GET /vehicles/GetMakesForManufacturerAndYear/{nameOrId}?year=` | Makes whose year range covers the year. Name LIKE. | `mer` and year 2013 returned 200, `Count` 217. A short string matches many manufacturers. |
| `GET /vehicles/GetMakesForVehicleType/{type}` | Makes for a vehicle type. LIKE match. | `car` returned 200, `Count` 195, vehicle type "Passenger Car". |
| `GET /vehicles/GetVehicleTypesForMake/{make}` | Vehicle types for a make name. | `honda` returned 200, 5 rows. |
| `GET /vehicles/GetVehicleTypesForMakeId/{id}` | Same, by make id. | id 474 returned 200, 4 rows (motorcycle, passenger car, and two more in the count). |
| `GET /vehicles/GetModelsForMake/{make}` | Models for a make. `*` is documented to mean all makes and is described as slow. | `honda` returned 200, `Count` 362, 28,675 bytes. |
| `GET /vehicles/GetModelsForMakeId/{id}` | Models by make id. `0` is documented as all makes and described as slow. | id 474 returned 200, `Count` 361. |
| `GET /vehicles/GetModelsForMakeYear/make/{make}/modelyear/{year}` | Models for a make and year. Documented: year greater than 1995. Optional `vehicletype` segment. | Honda 2015 returned 200, `Count` 62. The 1995 boundary was not retested. |
| `GET /vehicles/GetModelsForMakeIdYear/makeId/{id}/modelyear/{year}` | Same, by id. | make id 474 and 2015 returned 200, `Count` 62. |
| `GET /vehicles/GetAllManufacturers` | Manufacturers, 100 per page via `page`. Optional `ManufacturerType`. | page 1 returned 200, `Count` 100. |
| `GET /vehicles/GetManufacturerDetails/{nameOrId}` | Details. Numeric id is exact. A string is a LIKE match, 100 per page. | `honda` returned 200, `Count` 14. Rows include street address, email, phone, and principal name. Do not put those fields in a model context. |
| `GET /vehicles/GetParts` | Part 565 or 566 letters. `type` is 565 or 566. Optional `fromDate`, `toDate`, `manufacturer`, `page`. Documented page size 1000. | type 565, 1/1/2015 to 5/5/2015, page 1 returned 200, `Count` 174. These are submission letters, not a parts catalog. |
| `GET /vehicles/GetEquipmentPlantCodes` | Equipment plant codes. The hidden help says year 2016 and above, equipment types 1 tires, 3 brake hoses, 13 glazing, 16 retread, and report types New, Updated, Closed, All. | The path form printed in the page's `<kbd>` (`/GetEquipmentPlantCodes/2016`) returned 404. The query form used by the working sample links (`?year=2016&equipmentType=1&reportType=all`) returned 200, `Count` 1249, about 281 KB. The `<kbd>` example uses 2015 while the help text says 2016 and above. |
| `GET /vehicles/GetVehicleVariableList` | The variable dictionary. | 200, `Count` 145, about 48 KB. Fields include `ID`, `Name`, `GroupName`, `DataType`, `Description` (HTML). |
| `GET /vehicles/GetVehicleVariableValuesList/{nameOrId}` | Allowed values for a lookup variable. The page says to use the full name. | `battery type` returned 200, 9 values (lead acid, NiMH, Li-ion, and others). |
| `GET /vehicles/GetCanadianVehicleSpecifications/?year=&make=` | Transport Canada dimension records. Documented year >= 1971. Optional `model` and `units` (`Metric` default, or `US`). | 2011 Acura MDX returned 200, `Count` 1, content type `text/json` rather than `application/json`. |

Manufacturer type codes documented on the API page: 2 completed vehicle, 3 incomplete, 4 intermediate, 5 final-stage, 6 alterer, 7 fabricating equipment manufacturer, 8 equipment importer, 9 vehicle importer for FMVSS, 10 replica.

### Standalone vPIC database

[Downloads](https://vpic.nhtsa.dot.gov/downloads/) says the standalone databases are for local VIN decoding, that the API has quotas and rate limits (no number is published), and that the download decodes VINs only. Makes, models, variables, and attributes still need the API.

Observed file names on that page at research time:

| File | Engine | Size stated on the page | Updated |
| --- | --- | --- | --- |
| `vPICList_lite_2026_11.bak.zip` | SQL Server 2019 and newer | 180 MB | 2026-11-14 |
| `vPICList_lite_2026_11.custom.zip` | PostgreSQL 17 and newer, custom format | 67.0 MB | 2026-11-14 |
| `vPICList_lite_2026_11.plain.zip` | PostgreSQL 17 and newer, plain SQL | 72.8 MB | 2026-11-14 |

Restore lands in a schema named `vpic` for Postgres. Decode with `vpic.spVinDecode(vin)` or `vpic.spVinDecodeMultiple(array)`. SQL Server uses `dbo.spVinDecode` and a table-valued parameter. ([Downloads](https://vpic.nhtsa.dot.gov/downloads/), [parameter FAQ](https://vpic.nhtsa.dot.gov/Downloads/FAQ))

`spVinDecode` parameters documented there: VIN (required, up to 17), optional IncludePrivate, Year, IncludeAll, NoOutput. `spVinDecodeMultiple` is documented at a maximum of 100 VINs, which is a different cap from the HTTP batch cap of 50.

[Release notes](https://vpic.nhtsa.dot.gov/Downloads/ReleaseNotes) show a database refresh about once a month through 2026 (14 Nov, 17 Oct, 19 Sep, 15 Aug, and similar dates back through 2025). A monthly cadence is the pattern of those notes. The page does not promise a calendar day. Version 4.11 on 2026-11-14 is the one matching the file names above. Version 4.10 (2026-10-17) added Plant Address to the decode APIs, per the [API release notes](https://vpic.nhtsa.dot.gov/api/Home/Index/ReleaseNotes).

Requiring Postgres 17 or SQL Server 2019 just to answer one VIN is a heavy default. Offline decode should be optional. See the architecture doc.

## 2. Recalls

Documented on the [datasets page](https://www.nhtsa.gov/nhtsa-datasets-and-apis).

Manufacturers file a defect or noncompliance report under 49 CFR Part 573. The page's metadata says the dataset runs from 1949 to the present and is updated daily. The layout file [RCL.txt](https://static.nhtsa.gov/odi/ffdd/rcl/RCL.txt), fetched 2026-11-22, says the flat file contains safety defect and compliance campaigns since 1967. Those two start years disagree. Treat 1967 as the flat-file claim and 1949 as the datasets-page metadata, and do not paper over it.

The layout file also says records are tab-delimited, dates in the file are `YYYYMMDD`, and the maximum record length is 17,108. Fields include campaign number, make, model, model year (`9999` if unknown), component, a defect summary up to 6,000 characters, consequence, corrective action, notes, and two advisory flags added in the May 2025 changelog: Do Not Drive and Park Outside.

### Recall API

Host: `https://api.nhtsa.gov`. No key was required.

| Call | Documented | Observed |
| --- | --- | --- |
| `GET /recalls/recallsByVehicle?make=&model=&modelYear=` | Yes. Example on the datasets page is Acura RDX 2012. The page says method names and parameters are case sensitive. | 200. Acura RDX 2012: `Count` 2, 3,415 bytes. Honda Civic 2018: `Count` 6, 7,482 bytes. |
| `GET /recalls/campaignNumber?campaignNumber=` | Yes. Example `12V176000`. | 200. 1,370 bytes. One BMW 3-series row. This response included `PotentialNumberofUnitsAffected`. The by-vehicle responses we saved did not include that key. |
| `GET /recalls/recallsByVin` | Not documented. | 403, body `{"message":"Missing Authentication Token"}`, 42 bytes. That is the API Gateway body for a route that is not deployed. It is not evidence of a hidden VIN API. See the rate-limit doc. |

Successful recall JSON uses `Count`, `Message`, and lowercase `results`. Row fields we saw: `Manufacturer`, `NHTSACampaignNumber`, `parkIt`, `parkOutSide`, `overTheAirUpdate`, `ReportReceivedDate`, `Component`, `Summary`, `Consequence`, `Remedy`, `Notes`, `ModelYear`, `Make`, `Model`. The Acura row also had `NHTSAActionNumber` (`EA15001`), which is the link to an investigation. The campaign lookup added `PotentialNumberofUnitsAffected`.

`ReportReceivedDate` values we saw were `30/10/2017`, `06/03/2019`, `20/04/2012`, and `28/05/2020`. The first, third, and fourth only make sense as day/month/year. The flat file uses `YYYYMMDD`. The agent must not assume US month/day dates on the API.

Make and model matching is exact in practice and picky. `make=BMW&model=X3&modelYear=2011` returned 4 campaigns. The same make and year on `/products/vehicle/models` did not list `X3` at all (see below). A query that returns `Count` 0 can mean "that spelling has no rows," not "this vehicle was never recalled."

There is no public field for whether a specific VIN has already been repaired. The datasets page does not offer that. NHTSA's consumer VIN lookup on the website is a different system and was not verified as an API. The agent must not say a recall is open or closed on a particular car.

### Recall flat files

The datasets page lists daily files. A HEAD on 2026-11-22 returned 200 and `Last-Modified: Sat, 21 Nov 2026 08:03:58 GMT` for both pre and post 2010 zips. HEAD did not send `Content-Length`. Sizes below are the ones shown on the datasets page when it was retrieved the same day, not sizes we measured by downloading.

| File | Size on the datasets page | Role |
| --- | --- | --- |
| `FLAT_RCL_POST_2010.zip` | 14 MB | Campaigns from 2010 on. URL `https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip` |
| `FLAT_RCL_PRE_2010.zip` | 7 MB | Earlier campaigns. |
| `FLAT_RCL_Annual_Rpts.zip` | 184 KB | Annual reports. Not inspected. |
| `FLAT_RCL_Qrtly_Rpts.zip` | 1 MB | Quarterly reports. Not inspected. |
| `RCL.txt` | 3 KB | Layout. Fetched. 3,053 bytes. |

An older import PDF still says the file was named `FLAT_RCL.zip` and gives a shorter maximum record length. The current layout file is the authority for field sizes. ([RCL.txt](https://static.nhtsa.gov/odi/ffdd/rcl/RCL.txt))

## 3. Complaints

The datasets page describes the Office of Defects Investigation complaint file: owner complaints used to spot defect trends and to check recall scope. Metadata there says 1949 to the present, updated daily. [CMPL.txt](https://static.nhtsa.gov/odi/ffdd/cmpl/CMPL.txt) says the flat file contains complaints received since 1 January 1995. Same kind of disagreement as recalls. The flat-file statement is the one attached to the file.

### Complaint API

| Call | Observed |
| --- | --- |
| `GET /complaints/complaintsByVehicle?make=&model=&modelYear=` | Acura RDX 2012: 200, `count` 15, 17,032 bytes. Honda Civic 2018: 200, `count` 596, 576,788 bytes, about 1.9 seconds. `count` matched the array length. No paging parameter was required or offered. |
| `GET /complaints/odinumber?odinumber=1` | 200, `count` 0. The route exists. We did not look up a real ODI number, on purpose. |

JSON keys are lowercase: `count`, `message`, `results`. Each result had: `odiNumber`, `manufacturer`, `crash`, `fire`, `numberOfInjuries`, `numberOfDeaths`, `dateOfIncident`, `dateComplaintFiled`, `vin`, `components`, `summary`, `products`.

`products` is a list of objects with `type`, `productYear`, `productMake`, `productModel`, `manufacturer`.

The first Acura row's `vin` was 11 characters long. That matches the flat file, which defines VIN as `CHAR(11)`, not a full 17-character VIN. `summary` is the narrative. On the Acura set the longest narrative was 1,889 characters. On the Civic set the longest was 2,027 characters, and the totals were 25 crashes, 4 fires, 21 injuries, and 1 death. Those counts are from boolean and integer fields, not from reading the narratives.

A 577 KB complaint body is on the order of 140,000 tokens at a rough 4 characters per token. That figure is an estimate, not a tokenizer run. Returning it to a model is a bug. The Civic query is one popular car, not a worst case. We did not search for the largest model.

Narratives and the 11-character VIN can carry personal detail even though NHTSA redacts them. The flat-file layout also has consumer city and state. Those two were not top-level keys in the API rows we saw. The agent should not request the flat file's city, state, or VIN columns, and the API tool should drop `vin` and, by default, `summary`.

### Complaint flat file

[CMPL.txt](https://static.nhtsa.gov/odi/ffdd/cmpl/CMPL.txt) (fetched, 9,982 bytes, `Last-Modified` 1 May 2026) says the file is tab-delimited, dates are `YYYYMMDD`, and the maximum record length is 2,824. It still contains a June 2021 note about a content discrepancy after a system update, and says the note will stay until the issue is resolved. The data zip's `Last-Modified` was 21 November 2026. We did not compare file versions, so we do not know whether that 2021 note is still operationally true. The April 2026 changelog added field 50 (state of incident) and field 51 (vehicle operator).

The datasets page listed `FLAT_CMPL.zip` at 360 MB, updated 21 November 2026. HEAD returned 200 and that last-modified time, without a content length. Five-year chunks also exist (`COMPLAINTS_RECEIVED_YYYY-YYYY.zip`). We did not open them.

Do not ship a local copy of the full complaint file in v1. It is large, it contains partial VINs and narratives, and the API can answer a single model year if the shaper reduces it to counts.

## 4. NCAP safety ratings

The datasets page describes the New Car Assessment Program: crashworthiness stars, rollover, and crash-avoidance tests. Metadata says the dataset was released 5 January 2010, covers 1990 to the present, and is updated annually. A rating of five stars is the highest and one star is the lowest. Tests are run under contract laboratories.

### Ratings API

Base `https://api.nhtsa.gov/SafetyRatings`. Documented paths:

| Path | Observed |
| --- | --- |
| `/SafetyRatings` | 200, `Count` 38. The first years were 2027, 2026, 2025, descending. 38 years is consistent with 1990 through 2027 if the list is contiguous. We did not print the last element. A separate call to `/modelyear/1990` returned 200 (1,596 bytes). `/modelyear/2026` returned 200. |
| `/SafetyRatings/modelyear/{year}` | 2013 returned 200, 1,984 bytes. |
| `/SafetyRatings/modelyear/{year}/make/{make}` | 2013 Acura returned 200, 8 models: ILX, ILX HYBRID, MDX, RDX, TL, TSX, TSX SPORT WAGON, ZDX. `VehicleId` was 0 at this level. |
| `/SafetyRatings/modelyear/{year}/make/{make}/model/{model}` | 2013 Acura RDX returned 200, two variants: "2013 Acura RDX SUV 4WD" id 7731 and "2013 Acura RDX SUV FWD" id 7520. Lowercase `acura` and `rdx` returned the same body. This hop is case-insensitive in the one pair we tried. The datasets page still says parameters are case sensitive for the recalls section. Do not assume one rule covers both APIs. |
| `/SafetyRatings/VehicleId/{id}` | 7520 and 7731 both returned 200, 937 bytes. |

Vehicle fields observed: `OverallRating`, front and side ratings, side barrier and pole fields, `RolloverRating`, rollover possibility, `dynamicTipResult`, `SidePoleCrashRating`, `NHTSAElectronicStabilityControl`, `NHTSAForwardCollisionWarning`, `NHTSALaneDepartureWarning`, `ComplaintsCount`, `RecallsCount`, `InvestigationCount`, plus year, make, model, description, and id.

Both documented-sample variants came back `Not Rated` on the overall, front, side, rollover, and pole fields. 7731 still reported `ComplaintsCount` 163, `RecallsCount` 4, and `InvestigationCount` 1. `Not Rated` is data. It is not one star and it is not "safe." We did not capture a vehicle whose stars were a number, so the numeric encoding was not observed. The datasets page is the source for the 1-to-5 meaning.

`/SafetyRatings/modelyear/2011/make/BMW/model/X3` returned `Count` 0. The vPIC model string is not a reliable NCAP key. The zero can mean "no rated variant under that string." It does not, by itself, prove the model was never tested under another name.

These embedded complaint, recall, and investigation counts were not cross-checked against the complaints and recalls APIs. Do not treat them as the same query.

## 5. Investigations

The datasets page describes the defect-investigation process and, unlike recalls and complaints, offers a download rather than a REST example. [Resources Related to Investigations and Recalls](https://www.nhtsa.gov/resources-investigations-recalls) says NHTSA opens several kinds of investigations, including defect petitions, preliminary evaluations, recall queries, and engineering analyses, and that the public record is searchable on NHTSA.gov by open or close date and by NHTSA id. It points bulk download back at the datasets page.

[INV.txt](https://static.nhtsa.gov/odi/ffdd/inv/INV.txt) says the file contains investigations opened since 1972, tab-delimited, dates `YYYYMMDD`, maximum record length 6,816. Fields:

| Field | Meaning |
| --- | --- |
| NHTSA ACTION NUMBER | Id, 10 characters. The prefix is the type (PE, EA, and others). The layout file does not enumerate the prefixes. |
| MAKE, MODEL, YEAR | Year `9999` if unknown. |
| COMPNAME | Component. |
| MFR_NAME | Manufacturer. |
| ODATE, CDATE | Opened and closed. |
| CAMPNO | Recall campaign if the investigation led to one. |
| SUBJECT | Up to 200 characters. |
| SUMMARY | Up to 6,000 characters. |

`FLAT_INV.zip` is listed at 4 MB on the datasets page, and HEAD on 2026-11-22 returned 200 with `Last-Modified: Sat, 21 Nov 2026 09:08:42 GMT`. The layout file's own "last updated" line says 5 September 2023, which is the schema changelog, not the data refresh.

A guessed route, `/investigations/investigationsByVehicle`, returned the same 403 `Missing Authentication Token` as the other unknown routes. No public investigations REST API was found in the NHTSA pages we read. **Unknown** whether some undocumented route exists. Do not depend on one.

Four megabytes, refreshed daily, is small enough to download on startup and search locally. That is the v1 plan. The action-number prefix tells the investigation type. Publishing a type legend would require a source we do not have yet; until then, return the id and let the text speak.

## 6. Manufacturer communications

The datasets page says manufacturers must submit communications to dealers, owners, and similar parties about defects or failures, whether or not they are safety recalls. Files are chunked by the year NHTSA received them. [TSBS.txt](https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS.txt) (the layout, still named TSBS.txt; the changelog says it was renamed in spirit to MfrComms.txt on 13 May 2024) says:

- Communications received since 1 January 1995.
- A CSV with a short column set, one row per document per product, meant for keyword search of the summary.
- A TSV flat file with one row per combination of multi-valued fields. Five products and three components become 15 rows.
- Communication types listed in the file: Service Bulletin / Repair Instructions, Service Campaign, Warranty Program / Extension, Over The Air, Emissions, Other.
- Summary up to 4,000 characters. Component system and subsystem lengths were raised to 512 on 15 September 2026.

HEAD of `TSBS_RECEIVED_2020-2024.zip` and `MFR_COMMS_RECEIVED_2020-2024.zip` returned 200, last modified 21 November 2026. The datasets page showed the 2020 to 2024 TSV chunk at 30 MB and the CSV chunk at 11 MB. We did not download them.

A guessed REST path returned 403 `Missing Authentication Token`. No communications API was found in the pages we read.

These files are the right way to answer "is there a service bulletin," and they are also easy to over-quote. Leave them out of v1. A later offline index can search the CSV summary and return the document id, date, type, and a short summary, with a link back to NHTSA rather than a pasted bulletin.

## 7. The products enumeration API

The recalls section of the datasets page documents a second way to walk year, then make, then model:

- `GET /products/vehicle/modelYears?issueType=r`
- `GET /products/vehicle/makes?modelYear={year}&issueType=r`
- `GET /products/vehicle/models?modelYear={year}&make={make}&issueType=r`

Observed:

| Call | Result |
| --- | --- |
| `modelYears?issueType=r` | 200, `count` 20, years 1949 through 1968 only. |
| same with `page=2` | The same 20 years. `page` was ignored. |
| `modelYears` with no issue type | 200, 20 years as JSON numbers, including 1945, ending 1967. The `count` field was absent. |
| `modelYears?issueType=c` | 200, a different 20 years, sparse, ending 1974. |
| `makes?modelYear=2012&issueType=r` | 200, 15,480 bytes. A modern year works when you already know the year. |
| `models?modelYear=2012&make=ACURA&issueType=r` | 200, 13 rows, duplicates included (RDX twice, TL several times). |
| `models?modelYear=2011&make=BMW&issueType=r` | 200, 17 rows, 6 unique names: 128I, 135I, 323I, 325I, 328I, 328I XDRIVE. No X3, no X5. |
| `models?modelYear=2012&make=ACURA&issueType=c` | 200, 726 bytes, the same size as the recalls call. The bodies were not diffed. |

`issueType=r` is documented for recalls. `issueType=c` is not a value we found written down. It returned 200. **Unknown** what `c` is defined to mean, though complaints are the obvious guess. `issueType=i` also returned 200 and 20 early years. **Unknown** what `i` means. Do not label those letters in the tool docs until NHTSA's page is quoted for them.

The practical rule: do not use `modelYears` to build a year menu. Do not treat `models` as the list of spellings that have recalls. Query the recalls API with the decoded model, and if the result is empty, say the spelling may be wrong instead of saying there are no recalls.

## 8. Crash data

This is not a vehicle-spec catalog. It is included so the roadmap can reject it on purpose.

### FARS and the Crash API

[FARS](https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars) is a census of fatal injuries in motor vehicle traffic crashes. NHTSA tells people to use the FARS query tool or the FTP download of data from 1975 to the present.

The [Crash API](https://crashviewer.nhtsa.dot.gov/crashviewer/CrashAPI/) page says it serves FARS from 2010 onward as XML, CSV, XLSX, JSV, and JSON, and that several list calls are capped at 5,000 records. Documented families include case lists, case details, crashes by vehicle, by occupant, and by location, plus summary counts and a raw FARS export by dataset name.

Observed: `https://crashviewer.nhtsa.dot.gov/CrashAPI/...` (no extra path segment) returned the Crash Viewer HTML app, HTTP 200, `text/html`, behind Akamai, server header `Microsoft-IIS/10.0`. The same call under `https://crashviewer.nhtsa.dot.gov/crashviewer/CrashAPI/analytics/GetInjurySeverityCounts?fromCaseYear=2014&toCaseYear=2014&state=1&format=json` returned 200, `text/json`, 188 bytes, `Count` 1, with `CaseYear` 2014 and `CrashCounts` 747. The state code was not looked up. One successful call does not map the API.

A third-party README (see the roadmap) says this API returned an Akamai 403 on 2026-10-12. We did not see a 403 on 2026-11-22. Both can be true on different days. **Unknown** how stable the Crash API is.

FARS counts fatal crashes only. A make that appears often is usually a make with many vehicles, not a make that is unsafe. A v1 tool here would mostly produce bad answers. Leave it out.

### CISS and CRSS

[CRSS](https://www.nhtsa.gov/crash-data-systems/crash-report-sampling-system) is a sample of police-reported crashes of every severity. Public files omit names, addresses, and locations. [File downloads](https://www.nhtsa.gov/file-downloads) has `CISS/` and `CRSS/` folders. A 2024 CISS overview says that year's files are under the CISS 2024 folder. We did not download either system. They are statistical samples with weights. They are not a "was this VIN in a crash" service.

## 9. Adjacent data that is not this project

- Fuel economy is DOE and EPA, not NHTSA. Leave it out so the server does not pretend one agency published the other's numbers.
- Title, theft, odometer, and prior-accident history are commercial products. vPIC does not have them. The FAQ says decoding uses manufacturer 565 submissions, not state title records.
- Child seats, tires, and equipment show up inside recalls (`RCLTYPECD` in the flat file). v1 filters to vehicles. Equipment can be a later flag, not a separate product.
- CAFE compliance data exists on NHTSA's file site under `CAFE/`. We did not inventory it. It is a regulatory dataset, not a shopper's spec sheet.

## Quirks the design has to absorb

1. HTTP 200 does not mean the VIN decoded. Read `ErrorCode`.
2. An empty vPIC field means unknown, not "the vehicle lacks this." `Not Applicable` means it does not apply. Those are different.
3. Recall, complaint, rating, and vPIC model strings disagree. BMW X3 2011 had recalls and had zero NCAP rows under that string, and it was missing from the products model list.
4. `modelYears` does not list modern years.
5. Recall API dates are day/month/year. Flat files are `YYYYMMDD`.
6. JSON key casing differs by API (`Results` vs `results`, `Count` vs `count`).
7. Complaint responses are unpaged and can be hundreds of kilobytes, with an 11-character VIN and a narrative on every row.
8. Ratings use the words `Not Rated`. The sample vehicle in NHTSA's own docs is Not Rated.
9. There is no public per-VIN repair status.
10. The equipment-plant path printed in the docs 404s. The query-string form works.
11. Manufacturer detail rows contain contact details. They do not belong in a vehicle profile.
12. The vPIC download decodes VINs only, and it wants Postgres 17 or SQL Server 2019.

## What we did not verify

- A complete official error-code dictionary beyond the strings returned for the inputs above.
- An `ErrorCode` of 0.
- The 50-VIN batch cap, and the behavior at 51.
- Whether `GetModelsForMakeYear` rejects model year 1995.
- A 6-character WMI that returns a row.
- Numeric NCAP stars. We only observed `Not Rated`.
- Whether rating-embedded recall and complaint counts match the other APIs.
- The full safety-ratings year array, element by element. We saw `Count` 38 and the newest years.
- Any investigations or manufacturer-communications REST API.
- The meaning of `issueType` values other than `r`.
- FARS state codes, the 5,000-row cap, and CISS or CRSS file layouts.
- Byte sizes of the zips. The datasets page numbers were read from that page, and HEAD did not echo `Content-Length`.
- Whether the June 2021 complaints-file warning is still a live data issue.
