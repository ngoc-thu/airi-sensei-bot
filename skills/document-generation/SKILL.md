---
name: document-generation
version: 1.0.0
description: Execute safe mathematical computations and generate structured Markdown analytical reports, tables, and documents.
author: Airi Sensei Team
tags: [math, calculation, document, reports, markdown]
---

# Airi Document Generation & Calculation Skill (`document-generation`)

## 1. Overview
This skill provides two core capabilities:
1. **100% Precise Math Calculation:** Evaluates complex arithmetic, financial equations, and compound interest using a sandboxed Python AST evaluator.
2. **Structured Document Generation:** Produces clean Markdown reports, meeting minutes, and comparison matrices for the user.

---

## 2. When to Use
- When exact mathematical results are required:
  - *"Tính giúp anh: (1250 * 45) / 1.1 + sqrt(144)"*
  - *"Tính lãi kép gửi tiết kiệm 500 triệu lãi 6.5%/năm sau 3 năm"*
- When the user asks for a structured document or summary:
  - *"Lập giúp anh bảng so sánh giữa SQLite và PostgreSQL"*
  - *"Tạo khung biên bản cuộc họp"*

---

## 3. Sandboxed Calculation Whitelist
The calculation engine strictly validates expressions using Python `ast.parse` and only permits safe mathematical symbols and functions:
- Constants: `pi`, `e`
- Functions: `sqrt`, `sin`, `cos`, `tan`, `log`, `log10`, `exp`, `abs`, `round`
- Prohibited: File I/O, imports, attribute access (`__class__`, etc.), exec/eval injection.

---

## 4. Input Specifications
- **`expression`** *(string, required for calculation)*: Mathematical expression string.
- **`document_type`** *(string, optional)*: Type of document (`"table"`, `"report"`, `"summary"`).
- **`topic`** *(string, optional)*: Subject matter of the report.

---

## 5. Expected Output
- Exact numerical answer accompanied by calculation steps.
- Cleanly formatted Markdown tables and headers.

---

## 6. Error Handling
- If expression syntax is invalid, pinpoint the error clearly and offer corrected syntax.
