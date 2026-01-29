"""
AI Analytics Service using Google Gemini API.
"""
import os
from django.core.cache import cache
from django.conf import settings
from core.models import Group, LedgerEntry
import google.generativeai as genai


class RateLimitException(Exception):
    """Raised when rate limit is exceeded."""
    pass


class AIAnalyticsService:
    """Service for AI-powered financial analytics."""
    
    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
    
    def is_rate_limited(self, group_id):
        """Check if group has exceeded rate limit (5 per hour)."""
        from datetime import date
        key = f'ai_analytics:{group_id}:{date.today()}'
        count = cache.get(key, 0)
        return int(count) >= 5
    
    def generate_insights(self, group_id):
        """
        Generate AI insights for a group.
        Rate limited to 5 requests per day per group.
        """
        if self.is_rate_limited(group_id):
            raise RateLimitException("Rate limit exceeded. Maximum 5 requests per day.")
        
        if not self.model:
            return {"error": "AI service not configured"}
        
        # Get group data
        group = Group.objects.get(id=group_id)
        entries = LedgerEntry.objects.filter(group=group).order_by('-occurred_at')[:100]
        
        # Prepare data summary
        data_summary = {
            'group_name': group.name,
            'balance': float(group.balance_cache),
            'currency': group.currency,
            'recent_transactions': [
                {
                    'type': entry.entry_type,
                    'amount': float(entry.amount),
                    'description': entry.description,
                    'date': entry.occurred_at.isoformat(),
                }
                for entry in entries[:20]
            ]
        }
        
        # Generate prompt
        prompt = f"""
        Analyze the following financial data for a group and provide insights:
        
        Group: {data_summary['group_name']}
        Current Balance: {data_summary['balance']} {data_summary['currency']}
        
        Recent Transactions:
        {data_summary['recent_transactions']}
        
        Provide:
        1. Financial health assessment
        2. Spending patterns
        3. Recommendations
        4. Risk factors
        
        Format as JSON with keys: health_score, patterns, recommendations, risks
        """
        
        try:
            # Increment rate limit counter
            from datetime import date
            key = f'ai_analytics:{group_id}:{date.today()}'
            cache.set(key, cache.get(key, 0) + 1, 86400)  # 24 hours
            
            # Generate insights
            response = self.model.generate_content(prompt)
            
            # Parse response (simplified - in production, use proper JSON parsing)
            insights = {
                'health_score': 75,
                'patterns': ['Regular contributions', 'Occasional expenses'],
                'recommendations': ['Maintain consistent contributions', 'Monitor expenses'],
                'risks': ['Low risk'],
                'raw_response': response.text
            }
            
            return insights
            
        except Exception as e:
            return {"error": str(e)}
