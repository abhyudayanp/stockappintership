import os
import requests
from .SentimentAnalysisBase import SentimentAnalysisBase

class FinbertSentiment(SentimentAnalysisBase):

    def __init__(self):
        self.api_url = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
        self.api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
        super().__init__()

    def _query_huggingface(self, text):
        if not self.api_key:
            print("WARNING: HUGGINGFACE_API_KEY is not set. Returning neutral sentiment.")
            return [{'label': 'neutral', 'score': 1.0}]
            
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": text}
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        if isinstance(result[0], list):
                            return result[0]
                        return result
                elif response.status_code == 503:
                    print(f"HuggingFace model loading (attempt {attempt+1}/{max_retries}). Waiting 15s...")
                    time.sleep(15)
                    continue
                else:
                    print(f"HuggingFace API error: {response.status_code} - {response.text}")
                    break
            except Exception as e:
                print(f"HuggingFace API exception: {e}")
                break
                
        return [{'label': 'neutral', 'score': 1.0}]

    def calc_sentiment_score(self):
        # We need to process each title
        sentiments = []
        scores = []
        
        for title in self.df['title']:
            # Strip HTML tags if any
            clean_title = title.split('</a>')[0].split('>')[-1] if '</a>' in title else title
            
            res = self._query_huggingface(clean_title)
            # Find the highest scoring label
            if res and len(res) > 0:
                best = max(res, key=lambda x: x.get('score', 0))
                label = best.get('label', 'neutral')
                score_val = best.get('score', 0)
                
                multiplier = 0
                if label == 'positive':
                    multiplier = 1
                elif label == 'negative':
                    multiplier = -1
                    
                sentiments.append([best])
                scores.append(multiplier * score_val)
            else:
                sentiments.append([{'label': 'neutral', 'score': 1.0}])
                scores.append(0.0)
                
        self.df['sentiment'] = sentiments
        self.df['sentiment_score'] = scores
