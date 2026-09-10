# E-Commerce Reviews Analyzer — Server

The server-side API for the **E-Commerce Reviews Analyzer**, responsible for collecting e-commerce reviews, performing sentiment analysis, and generating AI-powered summaries.

The backend is built with **FastAPI** and uses **DistilBERT** for sentiment classification and **Google Gemini** for generating concise summaries of customer feedback.

## 🚀 Features

* 🔗 Accept e-commerce product URLs
* 🕷️ Extract customer reviews from product pages
* 📄 Support configurable review page limits
* 🤖 Analyze review sentiment using DistilBERT
* 📊 Generate sentiment results
* 🧠 Generate AI-powered review summaries using Gemini
* ⚡ FastAPI REST API
* 🔄 Return structured analysis results to the client

## 🛠️ Tech Stack

* **Python**
* **FastAPI**
* **DistilBERT**
* **Hugging Face Transformers**
* **Google Gemini API**
* **Web Scraping**
* **REST API**

## 🔄 How It Works

```text
E-Commerce Product URL
        ↓
   Review Extraction
        ↓
   Review Processing
        ↓
   DistilBERT
        ↓
 Sentiment Analysis
        ↓
   Gemini AI
        ↓
 Review Summary
        ↓
    API Response
```

## 📡 API Endpoint

### Analyze Reviews

```http
POST /analyze
```

### Request

```json
{
  "url": "https://www.daraz.pk/...",
  "max_pages": 5
}
```

### Response

The API returns the extracted reviews along with their sentiment analysis and an AI-generated summary.

Example structure:

```json
{
  "reviews": [],
  "sentiment": {},
  "summary": "..."
}
```

## 🤖 AI Pipeline

### 1. Review Extraction

The server receives the product URL and extracts available customer reviews from the specified pages.

### 2. Sentiment Analysis

Each review is processed using **DistilBERT** to classify its sentiment.

### 3. Review Summarization

The analyzed feedback is passed to **Google Gemini**, which generates a concise summary highlighting the overall customer opinion.

## 🎯 Project Goal

The backend is designed to transform raw customer reviews into meaningful insights by combining **web scraping, NLP-based sentiment analysis, and generative AI**.

This allows users to quickly understand customer opinions without manually analyzing hundreds of reviews.
