# BigBurger AI - Synthetic Data Quick Reference

## Files Created

1. **`prototype/mock_data/synthetic_contracts.json`** (main data file)
   - 40 comprehensive contract documents
   - 4 regional subsidiaries + corporate level
   - 30 vendor contracts, 4 leases, 5 compliance documents

2. **`SYNTHETIC_DATA_GUIDE.md`** (comprehensive documentation)
   - Document categories and test scenarios
   - Data schema reference
   - Usage instructions

3. **`prototype/test_synthetic_data.py`** (validation & testing script)
   - Validates data structure
   - Loads and ingests data
   - Runs predefined test scenarios

## Quick Start

### Option 1: Replace Existing Data
```bash
cd prototype
cp mock_data/synthetic_contracts.json mock_data/contracts.json
python main.py
```

### Option 2: Test Synthetic Data
```bash
cd prototype

# Full validation and testing
python test_synthetic_data.py

# Validate only
python test_synthetic_data.py --mode validate

# Test loading
python test_synthetic_data.py --mode load

# Run scenarios only
python test_synthetic_data.py --mode scenarios

# Specify different file
python test_synthetic_data.py --file mock_data/synthetic_contracts.json
```

## Key Synthetic Data Features

### Document Coverage

| Region | Vendor Contracts | Leases | Compliance | Total |
|--------|-----------------|--------|-----------|-------|
| North  | 6               | 1      | 1         | 8     |
| South  | 5               | 1      | 1         | 7     |
| East   | 5               | 1      | 1         | 7     |
| West   | 5               | 1      | 1         | 7     |
| Corp   | 1               | -      | -         | 1     |
| **Total** | **22**      | **4**  | **4**     | **40**|

### Testing Capabilities

✅ **Local Queries** - Regional manager accessing single region
✅ **Cross-Regional Queries** - Global auditor accessing all regions  
✅ **RBAC Enforcement** - Blocking unauthorized access
✅ **Conflict Detection** - FizzCo exclusivity conflicts (North/South vs East)
✅ **Aggregation** - Total liability across regions ($3.3M+ in leases)
✅ **Time-Sensitive** - Contracts expiring 2026, compliance deadlines
✅ **Multi-Supplier** - Same suppliers in different regions with varying terms
✅ **Cross-Default** - South Texas lease portfolio with cross-default clause
✅ **Compliance Tracking** - Multi-state health/safety requirements
✅ **National Conflicts** - Corporate FizzCo framework vs regional BubbleDrink exclusive

## Top Test Scenarios

### 1️⃣ Conflict Detection (HIGH PRIORITY)
**Goal**: Test cross-regional synthesis and conflict identification

**Query**: "Which regional subsidiaries have conflicting beverage exclusivity clauses?"

**Expected Findings**:
- North: FizzCo exclusive (Northern Territory)
- South: FizzCo exclusive (Southern Territory)  
- East: BubbleDrink exclusive WITH explicit FizzCo prohibition
- West: Mountain Springs (non-exclusive, allows FizzCo)
- **Conflict**: East's exclusivity prohibits FizzCo, creating conflict with potential national agreement
- **Liability Risk**: $1.2M in East if FizzCo is required nationally

**User**: `eve_auditor` (Global Auditor) - has cross-region access

---

### 2️⃣ Lease Aggregation (HIGH PRIORITY)
**Goal**: Test aggregation across multi-property portfolios

**Query**: "What are our total early termination liabilities for all regional lease agreements?"

**Expected Results**:
- North (Seattle HQ + Distribution): $210,000
- South (Texas 12 locations): $444,000  
- East (Northeast 8 locations): $1,100,000
- West (Western 15 locations): $1,575,000
- **TOTAL**: $3,329,000

**Additional Insight**: South lease has cross-default clause (high risk)

**User**: `frank_hq` (HQ Executive) - can aggregate

---

### 3️⃣ RBAC Enforcement (SECURITY CRITICAL)
**Goal**: Verify regional managers cannot access cross-regional data

**Query (Regional Manager)**: "Show me all contracts across all regions"

**Expected**: Request blocked or results limited to their region only

**Test Users**:
- `alice_north` - North only
- `bob_south` - South only
- `carol_east` - East only
- `dave_west` - West only

---

### 4️⃣ Authentication Failure (SECURITY)
**Goal**: Verify unauthorized users are rejected

**Query (Invalid User)**: `user_id="hacker_anon"` with any query

**Expected**: Authentication error, no data returned

---

### 5️⃣ Compliance Timeline (OPERATIONAL)
**Goal**: Track upcoming deadlines across regions

**Query**: "What compliance certifications, permits, and health inspections expire in 2026?"

**Expected Results**:
- **North**: Health permit renewal due Oct 31, 2026
- **South**: Hood cleaning cert due Mar 31, 2026 ⚠️ URGENT
- **East**: Allergen training deadline Mar 31, 2026 ⚠️ URGENT
- **West**: Food handler retraining due June 1, 2026

**User**: `frank_hq` (HQ Executive)

---

### 6️⃣ Local Query Performance (FUNCTIONALITY)
**Goal**: Verify basic single-region search works

**Query (Regional Manager)**: "When does our beef supply contract expire?"

**Expected**:
- North: PrimeBeef (expires Mar 15, 2026) ⚠️ NEAR TERM
- User: `alice_north` (North region only)
- Result: Single document returned

---

### 7️⃣ National Framework Conflict (STRATEGIC)
**Goal**: Test identification of corporate vs regional conflicts

**Query**: "What is the status of our FizzCo national beverage agreement and any regional conflicts?"

**Expected**:
- Corporate document: FizzCo National Framework (expires 2028)
- Conflict: East region BubbleDrink exclusive explicitly prohibits FizzCo
- Resolution: Requires legal review and potential amendment of East contract
- Liability Exposure: $1.2M early termination if East contract needs to be changed

**User**: `eve_auditor` or `frank_hq`

---

## Data Characteristics

### Liability Distribution
- **Total Across All Docs**: ~$11.3 million
- **Largest Single**: East lease ($1.1M early termination)
- **Largest Portfolio**: West lease ($1.575M across 15 locations)
- **Services/IT**: North TechServe ($900K/year)

### Contract Terms
- **Shortest**: Cleaning (North) - 1 year, expires Feb 28, 2025
- **Longest**: East lease - 11 years, expires Dec 31, 2031
- **Most Critical**: South Texas lease - 12 locations with cross-default clause

### Supplier Distribution
- **Food/Beverage**: 14 contracts (beef, dairy, tortillas, condiments, beverages)
- **Services**: 4 contracts (IT, logistics, cleaning, utilities)
- **Insurance**: 1 contract
- **Real Estate**: 4 lease agreements

## Document Metadata Examples

### Vendor Contract (North - FizzCo)
```json
{
  "doc_id": "north-bev-001",
  "region": "north",
  "supplier": "FizzCo Beverages Inc.",
  "expiry_date": "2027-06-30",
  "liability_amount": 750000,
  "tags": ["beverage", "exclusivity", "FizzCo"]
}
```

### Lease Agreement (East)
```json
{
  "doc_id": "east-lease-001",
  "region": "east",
  "landlord": "Atlantic Commercial Properties",
  "subsidiary": "BigBurger East LLC",
  "doc_type": "lease_agreement",
  "expiry_date": "2031-12-31",
  "liability_amount": 1100000
}
```

### Compliance Document (West)
```json
{
  "doc_id": "west-health-001",
  "region": "west",
  "doc_type": "compliance",
  "issuer": "Western Regional Health Authority",
  "tags": ["health_inspection", "compliance", "multi_state"]
}
```

## Integration with Google Drive (Production)

**Synthetic Data ↔ Google Drive Workflow**

```
Synthetic contracts.json (local testing)
           ↓
    Represents documents from:
           ↓
4 Google Drive folders (regional)
           ↓
Document AI (OCR for PDFs)
           ↓
Cloud Storage (staging)
           ↓
Chunker (this prototype)
           ↓
Vector Search (per-region)
```

To simulate Google Drive changes:
1. Modify `last_modified` and `version` fields
2. Re-run ingestion pipeline
3. Verify chunks update correctly (chunking idempotence)

## Troubleshooting Common Issues

### Issue: Data not loading
```bash
# Check file syntax
python -c "import json; json.load(open('mock_data/synthetic_contracts.json'))"

# View first document
python -c "import json; docs=json.load(open('mock_data/synthetic_contracts.json')); print(json.dumps(docs[0], indent=2))"
```

### Issue: Empty results for queries
- Verify region name matches (case-sensitive: north, south, east, west)
- Check document has matching content in "content" field
- Verify user has access to that region (RBAC check)

### Issue: Chunking produces too few/many chunks
- Default: 120 words per chunk, 20 word overlap
- Adjust `CHUNK_SIZE_WORDS` and `CHUNK_OVERLAP_WORDS` in config.py

---

**Version**: 1.0 | **Created**: April 2026 | **Test Scenarios**: 7 comprehensive scenarios
