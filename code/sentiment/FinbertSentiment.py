import os
import requests
from .SentimentAnalysisBase import SentimentAnalysisBase
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

class FinbertSentiment(SentimentAnalysisBase):

    def __init__(self):
        self.api_url = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
        self.api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
        
        # Render deployment fix: download NLTK data to /tmp
        nltk.data.path.append("/tmp/nltk_data")
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon', download_dir="/tmp/nltk_data")
        self.vader = SentimentIntensityAnalyzer()
        super().__init__()

    def _query_huggingface(self, text):
        if not self.api_key:
            return None
            
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": text}
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        if isinstance(result[0], list):
                            return result[0]
                        return result
                elif response.status_code == 503:
                    time.sleep(2)
                    continue
                else:
                    print(f"HuggingFace API error: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                print(f"HuggingFace API exception: {e}")
                return None
                
        return None

    def calc_sentiment_score(self):
        # We need to process each title
        sentiments = []
        scores = []
        
        for title in self.df['title']:
            # Strip HTML tags if any
            clean_title = title.split('</a>')[0].split('>')[-1] if '</a>' in title else title
            
            res = self._query_huggingface(clean_title)
            
            if res and len(res) > 0 and 'label' in res[0]:
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
                # Fallback to VADER
                vader_scores = self.vader.polarity_scores(clean_title)
                compound = vader_scores['compound']
                
                label = 'neutral'
                if compound >= 0.05:
                    label = 'positive'
                elif compound <= -0.05:
                    label = 'negative'
                    
                sentiments.append([{'label': label, 'score': abs(compound)}])
                scores.append(compound)
                
        self.df['sentiment'] = sentiments
        self.df['sentiment_score'] = scores
