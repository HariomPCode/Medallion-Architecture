# Finance-Complaints-Medallion

# AI-Augmented Medallion Pipeline for Financial Complaint Analytics

A cloud data pipeline on Microsoft Azure that turns raw consumer complaint data into business-ready summary tables using the **Medallion architecture** (Bronze → Silver → Gold). The Gold output is designed to feed a web frontend and an AI question-answering layer.

**Team:** [Vivek Sidhdhapura / Swarnadeep Samajdar / Saish Parab / Hariom Pandey]
**Guide:** [Anas Dange]
**Academic Year:** 2026–27

---

## Problem

Financial consumer complaint data is usually reviewed manually or through rigid batch processes. It is hard to trace, hard to scale, and hard for non-technical stakeholders to query. This project builds a governed, layered pipeline and exposes the results so insights can be reached without writing SQL.

## Architecture

```
Source CSVs → Bronze (raw) → Silver (cleaned) → Gold (aggregated) → Frontend / AI Q&A
```

| Layer | What it holds | Format |
|---|---|---|
| **Bronze** | Raw CSVs exactly as uploaded | CSV |
| **Silver** | Cleaned data: standardized column names, real date types, duplicates and null essentials removed | Delta tables + CSV |
| **Gold** | Business-ready summaries joined with the product-category reference | Delta tables + CSV |

## Dataset

Consumer complaints filed against financial products (mortgages, credit cards, money transfers, credit reporting and more), based on the CFPB Consumer Complaint Database.

- `Consumer_Complaints_AI.csv`: 62,516 complaint records, 12 columns
- `Product_Category_Reference.csv`: lookup table mapping each product to a Category and Sub-Category

## Pipeline Steps

1. **Bronze → Silver:** read with explicit schemas, rename columns, trim text, convert dates, drop rows missing essential fields, remove duplicate complaint IDs.
2. **Silver → Gold:** join complaints with the product-category reference (broadcast join), then aggregate:
   - complaints and timely-response percentage by Category and Sub-Category
   - complaint volume by year and Category
3. **Persist:** results saved as Delta tables and as CSV files in the `silver` and `gold` containers.

## Sample Gold Output

| Category | Sub-Category | Total Complaints | Timely Response % |
|---|---|---|---|
| Banking | Deposit Accounts | 24,814 | 93.6 |
| Payments | Card Products | 16,197 | 93.2 |
| Credit Reporting | Consumer Reporting | 7,710 | 91.4 |
| Lending | Real Estate Lending | 6,601 | 99.1 |

62,516 raw complaints are condensed into 9 category-level rows.

## Tech Stack

- Azure Data Lake Storage Gen2 (Bronze / Silver / Gold containers)
- Azure Databricks (Serverless), PySpark, Delta Lake
- Azure Storage Blob SDK for Python
- Databricks secret scope for credential handling
- Azure AI Foundry (planned, for the Q&A layer)


└── README.md
```

## How to Run

1. Create an Azure Storage account with hierarchical namespace enabled and three containers: `bronze`, `silver`, `gold`.
2. Upload the two CSVs from `data/` to the `bronze` container.
3. In Databricks, create a secret scope (`dbScope`) containing the storage account key under the name `StorageAccountKey`.
4. Import the notebooks into your Databricks workspace and run `Finance_Complaints_ADLS_Setup.ipynb` top to bottom.
5. Check the `silver` and `gold` containers for the output CSVs.

## Security Note

No credentials are stored in this repository. The storage key is read at runtime from the Databricks secret scope. Never commit keys, tokens, or `.env` files.

## Project Status

- [x] Bronze, Silver and Gold layers built and validated
- [x] Data quality notebook
- [ ] Backend API serving Gold data
- [ ] Frontend web application
- [ ] Automated ingestion with Azure Data Factory

## References

- Databricks, "What is the Medallion Architecture?"
- Microsoft Learn, Azure Databricks and Azure Data Lake Storage documentation
- Consumer Financial Protection Bureau, Consumer Complaint Database
