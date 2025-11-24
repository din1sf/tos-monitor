# ToS Monitor

**ToS Monitor** is a lightweight, serverless service running on **Google Cloud Run** that automatically tracks **Terms of Service (ToS)** and other legal documents.  
It downloads documents on a schedule, stores snapshots in **Cloud Storage**, and uses an **LLM** to generate human-readable summaries of changes.

It exposes three API endpoints:

1. **POST /fetch-docs** – Fetch and normalize the latest versions of all configured documents  
2. **POST /generate-diffs** – Compare snapshots and generate text-based diffs using an LLM  
3. **GET /diffs/...** – Retrieve the change summaries in plain text

All configuration, prompts, snapshots, and diffs are stored in Cloud Storage.

---

## ✨ Features

- Automatic weekly monitoring with Cloud Scheduler  
- Configurable document list in Cloud Storage  
- Prompts in Cloud Storage for per-document customization  
- Plain text diff reports (Markdown)  
- Snapshot history for auditing  
- Stateless Cloud Run service (no DB required)

---

## 🏗 Architecture Overview

```
Cloud Scheduler ───► POST /fetch-docs
                        ↓
                Cloud Run (ToS Monitor)
                        ↓
               Cloud Storage (snapshots/)
                        ↓
Cloud Scheduler ───► POST /generate-diffs
                        ↓
                   LLM comparison
                        ↓
            Cloud Storage (diffs/*.txt)
                        ↓
Client/UI ───► GET /diffs/<doc_id>
```

### Storage Layout

```
legal-watcher/
  config/
    documents.json
  prompts/
    default_comparison.txt
    <doc_id>.txt
  snapshots/
    <doc_id>/<timestamp>/raw.html
    <doc_id>/<timestamp>/normalized.txt
  latest/<doc_id>/normalized.txt
  latest/<doc_id>/meta.json
  diffs/<doc_id>/<timestamp>.txt
  diffs/<doc_id>/latest.txt
```

---

## 📜 Endpoints

### **POST /fetch-docs**
Downloads documents, normalizes them, and stores new snapshots when the content changes.

**Optional body:**
```json
{
  "doc_ids": ["anthropic_commercial_terms"]
}
```

---

### **POST /generate-diffs**
Reads the latest and previous snapshots, loads the appropriate LLM prompt from Storage, and generates plain-text diff summaries.

---

### **GET /diffs/<doc_id>**
Returns the latest human-readable diff text.

### **GET /diffs**
Lists all documents and latest diff timestamps.

### **GET /diffs/<doc_id>/<timestamp>**
Returns a specific diff.

---

## 🚀 Deployment

### 1. Create the bucket
```
gsutil mb -l europe-central2 gs://legal-watcher/
```

### 2. Upload initial config & prompt
```
gsutil cp config/documents.json gs://legal-watcher/config/
gsutil cp prompts/default_comparison.txt gs://legal-watcher/prompts/
```

### 3. Deploy to Cloud Run
```
gcloud run deploy tos-monitor   --source .   --region europe-central2   --allow-unauthenticated=false
```

### 4. Setup Cloud Scheduler

**Fetch weekly**
```
gcloud scheduler jobs create http fetch-docs   --schedule="0 7 * * 1"   --uri="https://<run-url>/fetch-docs"   --oidc-service-account="<invoker-sa>"
```

**Generate diffs**
```
gcloud scheduler jobs create http generate-diffs   --schedule="5 7 * * 1"   --uri="https://<run-url>/generate-diffs"   --oidc-service-account="<invoker-sa>"
```

---

## 🧠 LLM Prompt Example

File: `prompts/default_comparison.txt`

```
You analyze legal documents for substantive changes.

You will receive two versions of the same document: previous and current.

Produce a clear, concise, human-readable summary of what changed.
Use headings and bullet points. Focus on substance, not formatting.
If there are no meaningful changes, write: "No substantive changes detected."
```

---

## 🧪 Development

```
uvicorn app.main:app --reload
```

---

## 📂 Suggested Structure

```
app/
  main.py
  routes/
    fetch_docs.py
    generate_diffs.py
    get_diffs.py
  storage.py
  llm_client.py
  utils/
    html_parser.py
    normalizer.py
    hashing.py
Dockerfile
README.md
requirements.txt
```

---
