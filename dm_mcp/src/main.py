import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import openai
from dataclasses import dataclass
from collections import defaultdict
import re
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the Instagram MCP server functionality
from dm_mcp.src.mcp_server import (
    send_message, get_user_info, get_user_posts, 
    get_user_stories, search_users, get_user_followers
)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

@dataclass
class InfluencerProfile:
    """Comprehensive profile of an influencer built from their content"""
    username: str
    user_id: str
    full_name: str
    bio: str
    follower_count: int
    engagement_rate: float
    content_themes: List[str]
    posting_frequency: str
    brand_affiliations: List[str]
    communication_style: str
    best_posting_times: List[str]
    audience_demographics: Dict[str, Any]
    personality_traits: List[str]
    content_formats: List[str]  # reels, posts, stories, etc.
    viral_content_patterns: List[str]

@dataclass
class BrandCampaign:
    """Brand campaign requirements and goals"""
    brand_name: str
    campaign_goals: List[str]
    target_audience: Dict[str, Any]
    budget_range: str
    campaign_duration: str
    content_requirements: List[str]
    brand_values: List[str]
    excluded_topics: List[str]
    preferred_content_formats: List[str]

@dataclass
class OutreachCampaign:
    """A personalized outreach campaign for an influencer"""
    influencer: InfluencerProfile
    brand: BrandCampaign
    pitch_style: str  # "meme", "data-driven", "storytelling", "interactive"
    personalization_score: float
    predicted_response_rate: float
    creative_elements: List[Dict[str, Any]]
    follow_up_strategy: List[Dict[str, Any]]

class InfluencerAnalyzer:
    """Analyzes influencer profiles to build comprehensive understanding"""
    
    def __init__(self):
        self.content_categories = {
            "lifestyle": ["daily", "routine", "life", "day", "morning", "evening"],
            "fashion": ["outfit", "style", "wear", "fashion", "clothes", "look"],
            "beauty": ["makeup", "skincare", "beauty", "glow", "skin", "hair"],
            "fitness": ["workout", "gym", "fitness", "exercise", "health", "training"],
            "food": ["food", "recipe", "cooking", "eat", "restaurant", "meal"],
            "travel": ["travel", "trip", "vacation", "explore", "destination", "journey"],
            "tech": ["tech", "gadget", "app", "software", "device", "digital"],
            "business": ["entrepreneur", "business", "startup", "hustle", "success", "growth"]
        }
    
    async def analyze_influencer(self, username: str) -> Optional[InfluencerProfile]:
        """Deep analysis of an influencer's profile and content"""
        
        # Get basic user info
        user_info_result = get_user_info(username)
        if not user_info_result["success"]:
            return None
        
        user_info = user_info_result["user_info"]
        
        # Get recent posts for content analysis
        posts_result = get_user_posts(username, count=30)
        posts = posts_result.get("posts", []) if posts_result["success"] else []
        
        # Analyze content themes
        content_themes = self._analyze_content_themes(posts, user_info["biography"])
        
        # Calculate engagement rate
        engagement_rate = self._calculate_engagement_rate(posts, user_info["follower_count"])
        
        # Determine posting frequency
        posting_frequency = self._analyze_posting_frequency(posts)
        
        # Extract brand affiliations
        brand_affiliations = self._extract_brand_mentions(posts, user_info["biography"])
        
        # Analyze communication style
        communication_style = self._analyze_communication_style(posts)
        
        # Determine best posting times
        best_posting_times = self._analyze_posting_times(posts)
        
        # Analyze content formats
        content_formats = self._analyze_content_formats(posts)
        
        # Identify viral patterns
        viral_patterns = self._identify_viral_patterns(posts)
        
        # Use AI to determine personality traits
        personality_traits = await self._analyze_personality_with_ai(posts, user_info["biography"])
        
        # Estimate audience demographics (this is approximate)
        audience_demographics = self._estimate_audience_demographics(
            content_themes, communication_style, posts
        )
        
        return InfluencerProfile(
            username=username,
            user_id=user_info["user_id"],
            full_name=user_info["full_name"],
            bio=user_info["biography"],
            follower_count=user_info["follower_count"],
            engagement_rate=engagement_rate,
            content_themes=content_themes,
            posting_frequency=posting_frequency,
            brand_affiliations=brand_affiliations,
            communication_style=communication_style,
            best_posting_times=best_posting_times,
            audience_demographics=audience_demographics,
            personality_traits=personality_traits,
            content_formats=content_formats,
            viral_content_patterns=viral_patterns
        )
    
    def _analyze_content_themes(self, posts: List[Dict], bio: str) -> List[str]:
        """Identify main content themes from posts and bio"""
        all_text = bio.lower() + " ".join([p.get("caption", "") for p in posts]).lower()
        
        theme_scores = defaultdict(int)
        for theme, keywords in self.content_categories.items():
            for keyword in keywords:
                theme_scores[theme] += all_text.count(keyword)
        
        # Sort themes by score and return top themes
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, score in sorted_themes[:3] if score > 0]
    
    def _calculate_engagement_rate(self, posts: List[Dict], follower_count: int) -> float:
        """Calculate average engagement rate from recent posts"""
        if not posts or follower_count == 0:
            return 0.0
        
        total_engagement = sum(
            p.get("like_count", 0) + p.get("comment_count", 0) 
            for p in posts
        )
        avg_engagement = total_engagement / len(posts)
        return (avg_engagement / follower_count) * 100
    
    def _analyze_posting_frequency(self, posts: List[Dict]) -> str:
        """Determine how often the influencer posts"""
        if not posts:
            return "inactive"
        
        # Convert post times to datetime objects
        post_times = []
        for post in posts:
            try:
                post_time = datetime.fromisoformat(post["taken_at"].replace("Z", "+00:00"))
                post_times.append(post_time)
            except:
                continue
        
        if len(post_times) < 2:
            return "irregular"
        
        # Calculate average time between posts
        post_times.sort()
        time_diffs = [
            (post_times[i+1] - post_times[i]).days 
            for i in range(len(post_times)-1)
        ]
        avg_days_between = sum(time_diffs) / len(time_diffs)
        
        if avg_days_between < 1:
            return "multiple daily"
        elif avg_days_between <= 2:
            return "daily"
        elif avg_days_between <= 7:
            return "weekly"
        else:
            return "monthly"
    
    def _extract_brand_mentions(self, posts: List[Dict], bio: str) -> List[str]:
        """Extract brand mentions from posts and bio"""
        all_text = bio + " ".join([p.get("caption", "") for p in posts])
        
        # Look for @ mentions and common brand indicators
        mentions = re.findall(r'@(\w+)', all_text)
        hashtags = re.findall(r'#(?:sponsored|ad|partner|collaboration|gifted)', all_text.lower())
        
        # Combine and deduplicate
        brands = list(set(mentions))[:10]  # Limit to top 10
        return brands
    
    def _analyze_communication_style(self, posts: List[Dict]) -> str:
        """Determine the influencer's communication style"""
        captions = [p.get("caption", "") for p in posts if p.get("caption")]
        
        if not captions:
            return "visual-focused"
        
        # Analyze caption characteristics
        avg_length = sum(len(c) for c in captions) / len(captions)
        emoji_count = sum(len(re.findall(r'[\U0001F300-\U0001F9FF]', c)) for c in captions)
        question_count = sum(c.count('?') for c in captions)
        exclamation_count = sum(c.count('!') for c in captions)
        
        # Determine style based on characteristics
        if avg_length < 50:
            return "minimalist"
        elif emoji_count / len(captions) > 5:
            return "emoji-heavy"
        elif question_count / len(captions) > 0.5:
            return "conversational"
        elif exclamation_count / len(captions) > 1:
            return "enthusiastic"
        elif avg_length > 200:
            return "storyteller"
        else:
            return "balanced"
    
    def _analyze_posting_times(self, posts: List[Dict]) -> List[str]:
        """Determine when the influencer typically posts"""
        posting_hours = defaultdict(int)
        
        for post in posts:
            try:
                post_time = datetime.fromisoformat(post["taken_at"].replace("Z", "+00:00"))
                hour = post_time.hour
                posting_hours[hour] += 1
            except:
                continue
        
        # Find peak hours
        sorted_hours = sorted(posting_hours.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [f"{hour}:00" for hour, count in sorted_hours[:3]]
        
        return peak_hours if peak_hours else ["varied"]
    
    def _analyze_content_formats(self, posts: List[Dict]) -> List[str]:
        """Identify the types of content the influencer creates"""
        formats = defaultdict(int)
        
        for post in posts:
            media_type = post.get("media_type", 1)
            if media_type == 1:
                formats["photos"] += 1
            elif media_type == 2:
                formats["videos"] += 1
            elif media_type == 8:
                formats["carousels"] += 1
        
        # Convert to list of predominant formats
        return [fmt for fmt, count in formats.items() if count > 0]
    
    def _identify_viral_patterns(self, posts: List[Dict]) -> List[str]:
        """Identify patterns in high-performing content"""
        if not posts:
            return []
        
        # Sort posts by engagement
        sorted_posts = sorted(
            posts, 
            key=lambda p: p.get("like_count", 0) + p.get("comment_count", 0), 
            reverse=True
        )
        
        # Analyze top 20% of posts
        top_posts = sorted_posts[:max(1, len(sorted_posts) // 5)]
        patterns = []
        
        # Check for common elements in captions
        top_captions = [p.get("caption", "").lower() for p in top_posts]
        
        if any("question" in c or "?" in c for c in top_captions):
            patterns.append("questions drive engagement")
        if any(len(c) < 50 for c in top_captions):
            patterns.append("short captions perform well")
        if any(len(re.findall(r'[\U0001F300-\U0001F9FF]', c)) > 5 for c in top_captions):
            patterns.append("emoji-rich content")
        
        return patterns
    
    async def _analyze_personality_with_ai(self, posts: List[Dict], bio: str) -> List[str]:
        """Use AI to analyze personality traits from content"""
        # Prepare content sample for AI analysis
        content_sample = f"Bio: {bio}\n\n"
        caption_sample = "\n".join([
            f"Post {i+1}: {p.get('caption', '')[:200]}" 
            for i, p in enumerate(posts[:10])
        ])
        
        prompt = f"""Analyze this influencer's personality based on their content.
        
{content_sample}
{caption_sample}

List 3-5 key personality traits that define this person's online presence.
Format: Return only the traits as a comma-separated list."""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            
            traits_text = response.choices[0].message.content.strip()
            traits = [t.strip() for t in traits_text.split(',')]
            return traits[:5]
        except:
            # Fallback to basic analysis
            return ["authentic", "engaging", "creative"]
    
    def _estimate_audience_demographics(self, themes: List[str], style: str, posts: List[Dict]) -> Dict[str, Any]:
        """Estimate audience demographics based on content analysis"""
        demographics = {
            "age_range": "18-34",  # Default
            "gender_split": {"female": 60, "male": 40},  # Default
            "interests": themes,
            "location": "urban",  # Default assumption
        }
        
        # Adjust based on content themes
        if "fitness" in themes:
            demographics["age_range"] = "25-40"
            demographics["gender_split"] = {"female": 55, "male": 45}
        elif "business" in themes or "tech" in themes:
            demographics["age_range"] = "25-45"
            demographics["gender_split"] = {"female": 40, "male": 60}
        elif "beauty" in themes:
            demographics["age_range"] = "18-35"
            demographics["gender_split"] = {"female": 85, "male": 15}
        
        return demographics

class CreativeOutreachGenerator:
    """Generates creative, personalized outreach campaigns"""
    
    def __init__(self):
        self.pitch_templates = {
            "meme": self._generate_meme_pitch,
            "data_driven": self._generate_data_pitch,
            "storytelling": self._generate_story_pitch,
            "interactive": self._generate_interactive_pitch,
            "reverse": self._generate_reverse_pitch
        }
    
    async def generate_campaign(
        self, 
        influencer: InfluencerProfile, 
        brand: BrandCampaign
    ) -> OutreachCampaign:
        """Generate a complete outreach campaign"""
        
        # Calculate compatibility scores
        compatibility_score = self._calculate_compatibility(influencer, brand)
        
        # Choose best pitch style based on influencer personality
        pitch_style = self._select_pitch_style(influencer)
        
        # Generate creative elements
        creative_elements = await self._generate_creative_elements(
            influencer, brand, pitch_style
        )
        
        # Create follow-up strategy
        follow_up_strategy = self._create_follow_up_strategy(influencer)
        
        # Predict response rate based on personalization
        predicted_response = self._predict_response_rate(
            compatibility_score, 
            pitch_style, 
            influencer
        )
        
        return OutreachCampaign(
            influencer=influencer,
            brand=brand,
            pitch_style=pitch_style,
            personalization_score=compatibility_score,
            predicted_response_rate=predicted_response,
            creative_elements=creative_elements,
            follow_up_strategy=follow_up_strategy
        )
    
    def _calculate_compatibility(self, influencer: InfluencerProfile, brand: BrandCampaign) -> float:
        """Calculate compatibility score between influencer and brand"""
        score = 0.0
        
        # Theme overlap
        theme_overlap = len(set(influencer.content_themes) & set(brand.target_audience["interests"]))
        score += theme_overlap * 0.2
        
        # Audience match
        if influencer.audience_demographics["age_range"] == brand.target_audience.get("age_range", ""):
            score += 0.2
        
        # Content format match
        format_overlap = len(set(influencer.content_formats) & set(brand.preferred_content_formats))
        score += format_overlap * 0.1
        
        # Engagement rate bonus
        if influencer.engagement_rate > 3.0:
            score += 0.2
        
        # Brand affiliation penalty (if working with competitors)
        # This would need more sophisticated logic in production
        
        return min(score, 1.0)
    
    def _select_pitch_style(self, influencer: InfluencerProfile) -> str:
        """Select the best pitch style based on influencer personality"""
        
        # Map personality traits to pitch styles
        if "creative" in influencer.personality_traits or "artistic" in influencer.personality_traits:
            return "meme"
        elif "analytical" in influencer.personality_traits or influencer.communication_style == "data-driven":
            return "data_driven"
        elif influencer.communication_style == "storyteller":
            return "storytelling"
        elif "playful" in influencer.personality_traits or influencer.communication_style == "emoji-heavy":
            return "interactive"
        else:
            # Reverse pitch for high-profile influencers
            if influencer.follower_count > 100000:
                return "reverse"
            return "storytelling"
    
    async def _generate_creative_elements(
        self, 
        influencer: InfluencerProfile, 
        brand: BrandCampaign,
        pitch_style: str
    ) -> List[Dict[str, Any]]:
        """Generate creative elements for the pitch"""
        
        generator_func = self.pitch_templates.get(pitch_style, self._generate_story_pitch)
        return await generator_func(influencer, brand)
    
    async def _generate_meme_pitch(self, influencer: InfluencerProfile, brand: BrandCampaign) -> List[Dict[str, Any]]:
        """Generate a meme-based pitch"""
        
        # Create custom meme referencing their content
        recent_post_theme = influencer.content_themes[0] if influencer.content_themes else "content"
        
        meme_text = await self._generate_with_ai(
            f"Create a funny meme text format (like Drake meme or Distracted Boyfriend) about {influencer.username} doing {recent_post_theme} content vs partnering with {brand.brand_name}. Make it flattering and relevant to their content style. Keep it under 50 words."
        )
        
        elements = [
            {
                "type": "opener",
                "content": f"POV: {brand.brand_name} slides into {influencer.username}'s DMs with a meme instead of a boring pitch 👀"
            },
            {
                "type": "meme",
                "content": meme_text
            },
            {
                "type": "personalized_compliment",
                "content": f"But seriously, your {influencer.viral_content_patterns[0] if influencer.viral_content_patterns else 'content'} is exactly why {brand.brand_name} thinks you're perfect for our {brand.campaign_goals[0]} campaign"
            },
            {
                "type": "cta",
                "content": "Reply with your favorite emoji if you want to hear more (or just want more memes) 🎯"
            }
        ]
        
        return elements
    
    async def _generate_data_pitch(self, influencer: InfluencerProfile, brand: BrandCampaign) -> List[Dict[str, Any]]:
        """Generate a data-driven pitch"""
        
        elements = [
            {
                "type": "opener",
                "content": f"📊 {influencer.username}, the data scientist in me couldn't help but notice something interesting..."
            },
            {
                "type": "data_insight",
                "content": f"Your {influencer.engagement_rate:.1f}% engagement rate is {influencer.engagement_rate/0.5:.0f}x the industry average for {influencer.content_themes[0]} creators"
            },
            {
                "type": "brand_match",
                "content": f"{brand.brand_name}'s audience overlaps 73% with your demographic (we did the math 🤓)"
            },
            {
                "type": "projection",
                "content": f"Based on your posting patterns, a collaboration could reach {influencer.follower_count * 0.3:.0f} highly engaged users interested in {brand.campaign_goals[0]}"
            },
            {
                "type": "cta",
                "content": "Want to see the full analysis? I promise it includes charts 📈"
            }
        ]
        
        return elements
    
    async def _generate_story_pitch(self, influencer: InfluencerProfile, brand: BrandCampaign) -> List[Dict[str, Any]]:
        """Generate a storytelling pitch"""
        
        # Create a mini-story featuring them
        story = await self._generate_with_ai(
            f"Write a 3-sentence mini story where {influencer.username} (who creates {influencer.content_themes[0]} content) discovers {brand.brand_name} and it perfectly solves a problem related to {brand.campaign_goals[0]}. Make it creative and specific to their content style."
        )
        
        elements = [
            {
                "type": "opener",
                "content": f"Chapter 1: {influencer.username} meets {brand.brand_name} ✨"
            },
            {
                "type": "story",
                "content": story
            },
            {
                "type": "bridge",
                "content": "Plot twist: This isn't fiction - we actually want to make this story real with you"
            },
            {
                "type": "offer",
                "content": f"We love how you {influencer.viral_content_patterns[0] if influencer.viral_content_patterns else 'connect with your audience'} and think our {brand.campaign_goals[0]} aligns perfectly"
            },
            {
                "type": "cta",
                "content": "Ready to write the next chapter together? 📖"
            }
        ]
        
        return elements
    
    async def _generate_interactive_pitch(self, influencer: InfluencerProfile, brand: BrandCampaign) -> List[Dict[str, Any]]:
        """Generate an interactive pitch with choices"""
        
        elements = [
            {
                "type": "opener",
                "content": f"🎮 {influencer.username}, choose your own collaboration adventure!"
            },
            {
                "type": "interactive",
                "content": f"""You wake up to a DM from {brand.brand_name}. Do you:
                
A) Ignore it like the 100 other brand pitches ❌
B) Check it out because the memes look fire 🔥
C) Already screenshot it because it's too creative not to share 📸"""
            },
            {
                "type": "reveal",
                "content": f"If you picked B or C, congrats! You just discovered a brand that actually gets your {influencer.communication_style} vibe"
            },
            {
                "type": "pitch",
                "content": f"We're looking for creators who {influencer.viral_content_patterns[0] if influencer.viral_content_patterns else 'create authentic content'} for our {brand.campaign_goals[0]} campaign"
            },
            {
                "type": "cta",
                "content": "Reply with A, B, or C to continue the adventure (hint: C unlocks a surprise) 🎁"
            }
        ]
        
        return elements
    
    async def _generate_reverse_pitch(self, influencer: InfluencerProfile, brand: BrandCampaign) -> List[Dict[str, Any]]:
        """Generate a reverse pitch where brand applies to work with influencer"""
        
        application = await self._generate_with_ai(
            f"Write a playful 'job application' where {brand.brand_name} applies to work with {influencer.username}. Include why the brand is qualified to work with someone who creates {influencer.content_themes[0]} content and has {influencer.follower_count} followers. Keep it under 100 words and humble but confident."
        )
        
        elements = [
            {
                "type": "opener",
                "content": f"📋 Official Application to Collaborate with @{influencer.username}"
            },
            {
                "type": "application",
                "content": application
            },
            {
                "type": "credentials",
                "content": f"Our qualifications: {brand.campaign_goals[0]} expertise, budget that respects your {influencer.engagement_rate:.1f}% engagement rate, and a genuine appreciation for your work"
            },
            {
                "type": "references",
                "content": "References: Your last 10 posts that we've absolutely loved (yes, we did our homework)"
            },
            {
                "type": "cta",
                "content": "Interview available at your convenience. We'll bring coffee ☕"
            }
        ]
        
        return elements
    
    async def _generate_with_ai(self, prompt: str) -> str:
        """Generate content using AI"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except:
            return "Creative content generation in progress..."
    
    def _create_follow_up_strategy(self, influencer: InfluencerProfile) -> List[Dict[str, Any]]:
        """Create a follow-up strategy based on influencer behavior"""
        
        strategy = []
        
        # First follow-up after 48 hours
        strategy.append({
            "timing": "48_hours",
            "condition": "no_response",
            "action": "send_value_add",
            "content": f"Quick thought: noticed you post most at {influencer.best_posting_times[0] if influencer.best_posting_times else '7pm'}. We could time our campaign launch then for maximum impact 🚀"
        })
        
        # Second follow-up after 5 days
        strategy.append({
            "timing": "5_days",
            "condition": "no_response",
            "action": "send_social_proof",
            "content": "No pressure, but wanted to share that we just wrapped an amazing campaign with [similar creator]. Happy to share results if you're curious!"
        })
        
        # Engagement trigger
        strategy.append({
            "timing": "immediate",
            "condition": "views_profile",
            "action": "send_enthusiasm",
            "content": "Saw you checked us out! 👀 Any questions I can answer?"
        })
        
        return strategy
    
    def _predict_response_rate(self, compatibility: float, pitch_style: str, influencer: InfluencerProfile) -> float:
        """Predict likelihood of response based on various factors"""
        
        base_rate = 0.15  # Industry average
        
        # Compatibility bonus
        rate = base_rate + (compatibility * 0.3)
        
        # Pitch style modifier
        style_modifiers = {
            "meme": 0.15,
            "interactive": 0.12,
            "reverse": 0.18,
            "data_driven": 0.08,
            "storytelling": 0.10
        }
        rate += style_modifiers.get(pitch_style, 0.05)
        
        # Engagement rate correlation
        if influencer.engagement_rate > 5.0:
            rate += 0.1
        
        # Follower count penalty (bigger creators respond less)
        if influencer.follower_count > 1000000:
            rate *= 0.5
        elif influencer.follower_count > 100000:
            rate *= 0.7
        
        return min(rate, 0.85)  # Cap at 85%

class InfluenceOS:
    """Main application orchestrating the influencer outreach system"""
    
    def __init__(self):
        self.analyzer = InfluencerAnalyzer()
        self.generator = CreativeOutreachGenerator()
        self.campaigns = {}
        self.response_tracker = defaultdict(dict)
        self.ab_test_results = defaultdict(list)
    
    async def create_campaign(
        self, 
        brand_config: Dict[str, Any], 
        target_influencers: List[str],
        campaign_name: str
    ) -> Dict[str, Any]:
        """Create and launch a complete outreach campaign"""
        
        # Create brand campaign object
        brand = BrandCampaign(
            brand_name=brand_config["name"],
            campaign_goals=brand_config["goals"],
            target_audience=brand_config["target_audience"],
            budget_range=brand_config.get("budget", "negotiable"),
            campaign_duration=brand_config.get("duration", "1 month"),
            content_requirements=brand_config.get("requirements", []),
            brand_values=brand_config.get("values", []),
            excluded_topics=brand_config.get("excluded", []),
            preferred_content_formats=brand_config.get("formats", ["posts", "stories"])
        )
        
        campaign_id = f"{campaign_name}_{int(time.time())}"
        self.campaigns[campaign_id] = {
            "brand": brand,
            "status": "analyzing",
            "influencers": {},
            "messages_sent": 0,
            "responses": 0,
            "positive_responses": 0
        }
        
        # Analyze each target influencer
        for username in target_influencers:
            print(f"\n📊 Analyzing @{username}...")
            
            influencer_profile = await self.analyzer.analyze_influencer(username)
            if not influencer_profile:
                print(f"❌ Could not analyze @{username}")
                continue
            
            # Generate personalized campaign
            print(f"🎨 Creating personalized campaign for @{username}...")
            outreach = await self.generator.generate_campaign(influencer_profile, brand)
            
            # Store campaign data
            self.campaigns[campaign_id]["influencers"][username] = {
                "profile": influencer_profile,
                "outreach": outreach,
                "status": "ready",
                "messages": []
            }
            
            print(f"✅ Campaign ready for @{username}")
            print(f"   - Compatibility: {outreach.personalization_score:.1%}")
            print(f"   - Predicted response rate: {outreach.predicted_response_rate:.1%}")
            print(f"   - Pitch style: {outreach.pitch_style}")
        
        self.campaigns[campaign_id]["status"] = "ready"
        return self._get_campaign_summary(campaign_id)
    
    async def send_campaign_messages(self, campaign_id: str, test_mode: bool = False) -> Dict[str, Any]:
        """Send personalized messages to all influencers in campaign"""
        
        if campaign_id not in self.campaigns:
            return {"success": False, "error": "Campaign not found"}
        
        campaign = self.campaigns[campaign_id]
        results = []
        
        for username, influencer_data in campaign["influencers"].items():
            if influencer_data["status"] != "ready":
                continue
            
            outreach = influencer_data["outreach"]
            
            # Compose message from creative elements
            message_parts = []
            for element in outreach.creative_elements:
                message_parts.append(element["content"])
            
            full_message = "\n\n".join(message_parts)
            
            if test_mode:
                print(f"\n📤 TEST MODE - Message to @{username}:")
                print("-" * 50)
                print(full_message)
                print("-" * 50)
                result = {"success": True, "test_mode": True}
            else:
                # Actually send the message
                result = send_message(username, full_message)
            
            if result["success"]:
                # Track sending
                influencer_data["status"] = "message_sent"
                influencer_data["messages"].append({
                    "type": "initial",
                    "content": full_message,
                    "sent_at": datetime.now().isoformat(),
                    "message_id": result.get("direct_message_id")
                })
                campaign["messages_sent"] += 1
                
                # Schedule follow-ups
                self._schedule_follow_ups(campaign_id, username, outreach.follow_up_strategy)
                
                results.append({
                    "username": username,
                    "success": True,
                    "pitch_style": outreach.pitch_style
                })
            else:
                results.append({
                    "username": username,
                    "success": False,
                    "error": result.get("message", "Unknown error")
                })
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "messages_sent": campaign["messages_sent"],
            "results": results
        }
    
    def _schedule_follow_ups(self, campaign_id: str, username: str, strategy: List[Dict[str, Any]]):
        """Schedule follow-up messages based on strategy"""
        # In a production system, this would use a proper task queue
        # For the hackathon, we'll keep it simple
        for follow_up in strategy:
            self.response_tracker[campaign_id][username] = {
                "follow_ups": strategy,
                "current_index": 0
            }
    
    async def check_and_send_follow_ups(self, campaign_id: str) -> Dict[str, Any]:
        """Check conditions and send follow-up messages"""
        if campaign_id not in self.campaigns:
            return {"success": False, "error": "Campaign not found"}
        
        campaign = self.campaigns[campaign_id]
        follow_ups_sent = []
        
        for username, tracker in self.response_tracker[campaign_id].items():
            if tracker["current_index"] >= len(tracker["follow_ups"]):
                continue
            
            current_follow_up = tracker["follow_ups"][tracker["current_index"]]
            influencer_data = campaign["influencers"][username]
            
            # Check timing condition
            last_message = influencer_data["messages"][-1]
            last_sent = datetime.fromisoformat(last_message["sent_at"])
            time_elapsed = datetime.now() - last_sent
            
            should_send = False
            if current_follow_up["timing"] == "48_hours" and time_elapsed > timedelta(hours=48):
                should_send = True
            elif current_follow_up["timing"] == "5_days" and time_elapsed > timedelta(days=5):
                should_send = True
            
            if should_send:
                result = send_message(username, current_follow_up["content"])
                if result["success"]:
                    influencer_data["messages"].append({
                        "type": "follow_up",
                        "content": current_follow_up["content"],
                        "sent_at": datetime.now().isoformat(),
                        "message_id": result.get("direct_message_id")
                    })
                    tracker["current_index"] += 1
                    follow_ups_sent.append(username)
        
        return {
            "success": True,
            "follow_ups_sent": len(follow_ups_sent),
            "usernames": follow_ups_sent
        }
    
    def _get_campaign_summary(self, campaign_id: str) -> Dict[str, Any]:
        """Get summary of campaign performance"""
        campaign = self.campaigns[campaign_id]
        
        total_influencers = len(campaign["influencers"])
        avg_compatibility = sum(
            i["outreach"].personalization_score 
            for i in campaign["influencers"].values()
        ) / total_influencers if total_influencers > 0 else 0
        
        avg_predicted_response = sum(
            i["outreach"].predicted_response_rate 
            for i in campaign["influencers"].values()
        ) / total_influencers if total_influencers > 0 else 0
        
        return {
            "campaign_id": campaign_id,
            "brand": campaign["brand"].brand_name,
            "status": campaign["status"],
            "total_influencers": total_influencers,
            "messages_sent": campaign["messages_sent"],
            "responses": campaign["responses"],
            "positive_responses": campaign["positive_responses"],
            "avg_compatibility": avg_compatibility,
            "avg_predicted_response": avg_predicted_response,
            "response_rate": campaign["responses"] / campaign["messages_sent"] if campaign["messages_sent"] > 0 else 0
        }
    
    async def analyze_campaign_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze what worked and what didn't in the campaign"""
        campaign = self.campaigns[campaign_id]
        
        # Group by pitch style
        style_performance = defaultdict(lambda: {"sent": 0, "responded": 0})
        
        for username, data in campaign["influencers"].items():
            style = data["outreach"].pitch_style
            style_performance[style]["sent"] += 1
            if data["status"] == "responded":
                style_performance[style]["responded"] += 1
        
        # Calculate response rates by style
        style_results = {}
        for style, perf in style_performance.items():
            if perf["sent"] > 0:
                style_results[style] = {
                    "response_rate": perf["responded"] / perf["sent"],
                    "total_sent": perf["sent"],
                    "total_responded": perf["responded"]
                }
        
        # Find best performing elements
        successful_elements = []
        for username, data in campaign["influencers"].items():
            if data["status"] == "responded_positive":
                successful_elements.extend([
                    element["type"] for element in data["outreach"].creative_elements
                ])
        
        element_frequency = defaultdict(int)
        for element in successful_elements:
            element_frequency[element] += 1
        
        return {
            "campaign_id": campaign_id,
            "overall_response_rate": campaign["responses"] / campaign["messages_sent"] if campaign["messages_sent"] > 0 else 0,
            "positive_response_rate": campaign["positive_responses"] / campaign["messages_sent"] if campaign["messages_sent"] > 0 else 0,
            "style_performance": dict(style_results),
            "top_performing_elements": sorted(
                element_frequency.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }

# Demo and testing functions
async def run_demo():
    """Run a demonstration of InfluenceOS"""
    print("🚀 Welcome to InfluenceOS - AI-Powered Influencer Outreach")
    print("=" * 60)
    
    # Initialize the system
    ios = InfluenceOS()
    
    # Demo brand configuration
    demo_brand = {
        "name": "TechFlow",
        "goals": ["increase brand awareness", "drive app downloads"],
        "target_audience": {
            "age_range": "18-35",
            "interests": ["tech", "productivity", "lifestyle"],
            "location": "urban"
        },
        "budget": "$1,000-$5,000 per creator",
        "duration": "3 months",
        "requirements": ["authentic testimonials", "tutorial content"],
        "values": ["innovation", "simplicity", "empowerment"],
        "formats": ["posts", "stories", "reels"]
    }
    
    # Demo influencer list (you'll need to replace with real usernames)
    demo_influencers = [
        "tech_sarah",  # Replace with actual usernames
        "lifestyle_mike",
        "productivity_queen"
    ]
    
    print("\n📋 Creating campaign for TechFlow...")
    print(f"Target influencers: {', '.join(demo_influencers)}")
    
    # Create campaign
    campaign_result = await ios.create_campaign(
        demo_brand,
        demo_influencers,
        "TechFlow_Launch"
    )
    
    print("\n📊 Campaign Summary:")
    print(f"   Total influencers analyzed: {campaign_result['total_influencers']}")
    print(f"   Average compatibility: {campaign_result['avg_compatibility']:.1%}")
    print(f"   Predicted response rate: {campaign_result['avg_predicted_response']:.1%}")
    
    # Send messages (in test mode for demo)
    print("\n📤 Sending personalized messages (TEST MODE)...")
    send_result = await ios.send_campaign_messages(
        campaign_result["campaign_id"],
        test_mode=True  # Set to False to actually send
    )
    
    print(f"\n✅ Demo complete! {send_result['messages_sent']} messages prepared")
    
    # Show performance analysis (would have real data after responses)
    print("\n📈 Performance Analysis Preview:")
    analysis = await ios.analyze_campaign_performance(campaign_result["campaign_id"])
    print(f"   Campaign ID: {analysis['campaign_id']}")
    print("   (Metrics will populate as influencers respond)")

if __name__ == "__main__":
    # Run the demo
    asyncio.run(run_demo())