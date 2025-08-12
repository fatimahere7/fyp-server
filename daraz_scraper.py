from fastapi import FastAPI, HTTPException, Query
import requests
import re
from collections import defaultdict
from transformers import pipeline
import uvicorn
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import random
import time
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up Google Gemini API key
GENAI_API_KEY = "AIzaSyCoa2QoOG0pMGcOnTu83GAQkK99x_BcnYc"
genai.configure(api_key=GENAI_API_KEY)

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.daraz.pk/",
})

sentiment_analyzer = pipeline(
    'sentiment-analysis',
    model='distilbert-base-uncased-finetuned-sst-2-english',
    device=-1,
    truncation=True
)

class SummaryRequest(BaseModel):
    text: str

@app.post("/generate-summary")
def generate_summary(data: SummaryRequest):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(data.text)
        return {"summary": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_product_info(url: str) -> Dict[str, str]:
    for attempt in range(3):
        resp = session.get(url, timeout=10)
        if resp.status_code == 200 and "unusual traffic" not in resp.text.lower():
            html = resp.text
            name_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
            img_match  = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            return {
                "name":  name_match.group(1) if name_match else "",
                "image": img_match.group(1) if img_match else "",
            }
        time.sleep(random.uniform(1.0, 2.5))
    raise Exception("Blocked by Cloudflare / unusual traffic detected")

def get_daraz_reviews(url: str, max_pages: int = 8) -> List[Dict[str, Any]]:
    product_id = re.search(r'-i(\d+)', url)
    if not product_id:
        return []

    product_id = product_id.group(1)
    reviews = []

    for page in range(1, max_pages + 1):
        api_url = f"https://my.daraz.pk/pdp/review/getReviewList?itemId={product_id}&pageSize=20&filter=0&sort=0&pageNo={page}"
        try:
            response = session.get(api_url, timeout=10)
            data = response.json()
            items = data.get('model', {}).get('items', [])
            for item in items:
                reviews.append({
                    'author': item.get('buyerName'),
                    'rating': item.get('rating'),
                    'date': item.get('reviewTime'),
                    'content': item.get('reviewContent'),
                    'likes': item.get('likeCount')
                })
            if not items:
                break
        except Exception as e:
            print(f"Error fetching page {page}: {str(e)}")
            continue
        time.sleep(random.uniform(0.5, 1.5))
    return reviews

def analyze_reviews(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not reviews:
        return {
            'stats': {'total': 0},
            'issues': {}
        }

    sentiments = []
    for review in reviews:
        try:
            content = review['content'][:512]
            result = sentiment_analyzer(content)[0]
            sentiments.append(result['label'])
        except:
            sentiments.append('NEUTRAL')

    pos = sum(1 for s in sentiments if s == 'POSITIVE')
    neg = sum(1 for s in sentiments if s == 'NEGATIVE')
    neu = len(reviews) - pos - neg

    negative_reviews = [r for r, s in zip(reviews, sentiments) if s == 'NEGATIVE']
    issue_data = defaultdict(lambda: {'count': 0, 'reviews': []})

    issue_keywords = {
        'quality': ['poor quality', 'cheap quality', 'broken', 'defective','bura','bad quality','ghatiya','disappointing','looks bad','not same as shown','bad','low quality','tota','not woking'],
        'delivery': ['late', 'slow', 'shipping','dair'],
        'price': ['pricey', 'expensive', 'overpriced','waste of money'],
        'description': ['description', 'different','difference', 'wrong','bekaar','not good experience','bad experience','quatity kam','small quantity','less','paisy wapis','fraud','frad','lakin','wrong product','empty','scam'],
        'service': ['service', 'customer', 'support','rude','return']
    }

    for review in negative_reviews:
        content = review['content'].lower()
        for issue, keywords in issue_keywords.items():
            if any(keyword in content for keyword in keywords):
                issue_data[issue]['count'] += 1
                issue_data[issue]['reviews'].append({
                    'content': review['content'],
                    'rating': review['rating'],
                    'date': review['date'],
                    'likes': review['likes']
                })
                break

    sorted_issues = sorted(
        issue_data.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:5]

    return {
        'stats': {'total': len(reviews), 'positive': pos, 'negative': neg, 'neutral': neu},
        'issues': dict(sorted_issues)
    }

@app.get("/analyze")
async def analyze_product(
    url: str = Query(..., description="Daraz product URL"),
    max_pages: int = Query(1, description="Pages to scrape (1-6)", ge=1, le=6)
) -> Dict[str, Any]:
    try:
        if "daraz.pk" not in url:
            raise HTTPException(status_code=400, detail="Invalid Daraz URL")

        reviews = get_daraz_reviews(url, max_pages)
        info = get_product_info(url)
        if not reviews:
            return {
                "status": "success",
                "message": "No reviews found",
                "data": {
                    "reviews_count": 0,
                    "analysis": None
                }
            }

        analysis = analyze_reviews(reviews)

        # Generate summary from all reviews
        all_review_text = "\n".join([r['content'] for r in reviews if r.get('content')])
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            summary_response = model.generate_content(f"Summarize the following text in five bullet points,Each bullet must start with the emoji ⭐ (not an asterisk) ,each bullet must be only one sentence long,Use exactly 10 to 11 words per bullet,focus only on the main points and insights,do not include any headings, intros, or conclusions:\n\n{all_review_text}")
            summary_text = summary_response.text
        except Exception:
            summary_text = "Summary could not be generated."

        return {
            "status": "success",
            "data": {
                "product": {
                    "name": info["name"],
                    "image": info["image"]
                },
                "reviews_count": len(reviews),
                "sentiment": {
                    "positive": analysis['stats']['positive'],
                    "negative": analysis['stats']['negative'],
                    "neutral": analysis['stats']['neutral'],
                    "positive_percent": f"{analysis['stats']['positive']/len(reviews):.1%}",
                    "negative_percent": f"{analysis['stats']['negative']/len(reviews):.1%}"
                },
                "common_issues": [
                    {
                        "issue": issue,
                        "count": data['count'],
                        "reviews": data['reviews']
                    }
                    for issue, data in analysis['issues'].items()
                ],
                "all_reviews": reviews,
                "summary": summary_text
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
