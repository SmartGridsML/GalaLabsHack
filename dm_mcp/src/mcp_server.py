import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from firecrawl import FirecrawlApp, ScrapeOptions
import re

# Import client libraries for both services
from instagrapi import Client as InstagramClient
from twikit import Client as TwitterClient
import twikit.utils

# --- INITIAL SETUP ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- MCP SERVER INITIALIZATION ---
INSTRUCTIONS = """
This is a unified server that can interact with both Instagram and X (Twitter).
It can send DMs, post content, get timelines, and more on both platforms.
"""
mcp = FastMCP(
    name="Social Media Unified Server",
    instructions=INSTRUCTIONS
)

# --- GLOBAL CLIENTS AND CONFIG ---
instagram_client: Optional[InstagramClient] = None
twitter_client: Optional[TwitterClient] = None
firecrawl_client: Optional[FirecrawlApp] = None
COOKIES_PATH = Path('./twitter_cookies.json')

# =============================================================================
# --- TWITTER TOOLS ---
# =============================================================================
def get_tweet_data(tweet: twikit.Tweet) -> Dict:
    try:
        return {
            'id': tweet.id, 'text': tweet.text, 'username': tweet.user.screen_name,
            'user_id': tweet.user.id, 'created_at': tweet.created_at, 'likes': tweet.favorite_count,
            'replies': tweet.reply_count, 'retweets': tweet.retweet_count,
        }
    except Exception as e:
        logger.error(f"Error processing tweet data: {e}")
        return {'error': str(e)}

@mcp.tool()
async def get_tweets(query: str, sort_by: str = 'Latest', count: int = 20) -> List[dict]:
    """Search twitter with a query. Sort by 'Top' or 'Latest'."""
    if not twitter_client: return [{"error": "Twitter client not initialized."}]
    try:
        tweets = await twitter_client.search_tweet(query, sort_by, count=count)
        return [get_tweet_data(tweet) for tweet in tweets]
    except Exception as e: return [{"error": str(e)}]

@mcp.tool()
async def get_user_tweets(username: str, tweet_type: str = 'Tweets', count: int = 10) -> List[dict]:
    """Get tweets from a specific user's timeline."""
    if not twitter_client: return [{"error": "Twitter client not initialized."}]
    try:
        user = await twitter_client.get_user_by_screen_name(username.lstrip('@'))
        tweets = await twitter_client.get_user_tweets(user.id, tweet_type=tweet_type, count=count)
        return [get_tweet_data(tweet) for tweet in tweets]
    except Exception as e: return [{"error": str(e)}]

@mcp.tool()
async def post_tweet(text: str, media_paths: Optional[List[str]] = None) -> str:
    """Post a tweet with optional media."""
    if not twitter_client: return "Error: Twitter client not initialized."
    try:
        media_ids = [await twitter_client.upload_media(path, wait_for_completion=True) for path in media_paths] if media_paths else None
        tweet = await twitter_client.create_tweet(text=text, media_ids=media_ids)
        return f"Successfully posted tweet: {tweet.id}"
    except Exception as e: return f"Failed to post tweet: {e}"

@mcp.tool()
async def send_twitter_dm(username: str, text: str) -> Dict[str, Any]:
    """Sends a Direct Message to a user on Twitter."""
    if not twitter_client: return {"success": False, "message": "Twitter client not initialized."}
    if not username or not text: return {"success": False, "message": "Username and text must be provided."}
    try:
        user = await twitter_client.get_user_by_screen_name(username.lstrip('@'))
        if not user: return {"success": False, "message": f"Could not find Twitter user: {username}"}
        await twitter_client.create_dm(user.id, text)
        return {"success": True, "message": f"DM successfully sent to @{user.screen_name}."}
    except Exception as e: return {"success": False, "message": f"An error occurred: {e}"}

@mcp.tool()
async def list_twitter_dms(count: int = 20) -> Dict[str, Any]:
    """Lists the most recent Twitter DM conversations."""
    if not twitter_client: return {"success": False, "message": "Twitter client not initialized."}
    try:
        inbox = await twitter_client.get_dm_inbox(count=count)
        conversations = [{
                "conversation_id": conv.id,
                "participants": [p.screen_name for p in conv.participants if p.id != twitter_client.user.id],
                "last_message": conv.messages[0].text if conv.messages else "[No messages]",
                "timestamp": conv.messages[0].created_at if conv.messages else ""
            } for conv in inbox.conversations]
        return {"success": True, "conversations": conversations}
    except Exception as e: return {"success": False, "message": f"An error occurred: {e}"}

# =============================================================================
# --- ALL 20 INSTAGRAM TOOLS (RESTORED & ASYNC-SAFE) ---
# =============================================================================

@mcp.tool()
async def send_message(username: str, message: str) -> Dict[str, Any]:
    """Send an Instagram direct message to a user by username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username or not message: return {"success": False, "message": "Username and message must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            dm = instagram_client.direct_send(message, [user_id])
            return {"success": True, "message": "Message sent.", "direct_message_id": getattr(dm, 'id', None)} if dm else {"success": False, "message": "Failed to send message."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def send_photo_message(username: str, photo_path: str) -> Dict[str, Any]:
    """Send a photo via Instagram direct message to a user by username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username or not photo_path: return {"success": False, "message": "Username and photo_path must be provided."}
        if not os.path.exists(photo_path): return {"success": False, "message": f"Photo file not found: {photo_path}"}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            result = instagram_client.direct_send_photo(Path(photo_path), [user_id])
            return {"success": True, "message": "Photo sent successfully."} if result else {"success": False, "message": "Failed to send photo."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def send_video_message(username: str, video_path: str) -> Dict[str, Any]:
    """Send a video via Instagram direct message to a user by username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username or not video_path: return {"success": False, "message": "Username and video_path must be provided."}
        if not os.path.exists(video_path): return {"success": False, "message": f"Video file not found: {video_path}"}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            result = instagram_client.direct_send_video(Path(video_path), [user_id])
            return {"success": True, "message": "Video sent successfully."} if result else {"success": False, "message": "Failed to send video."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def list_chats(amount: int = 20, selected_filter: str = "", thread_message_limit: Optional[int] = None, full: bool = False, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get Instagram Direct Message threads (chats) from the user's account, with optional filters and limits."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        def thread_summary(thread):
            t = thread.dict()
            users = t.get("users", [])
            user_summaries = [{"username": u.get("username"), "full_name": u.get("full_name"), "pk": u.get("pk")} for u in users]
            return {"thread_id": t.get("id"), "thread_title": t.get("thread_title"), "users": user_summaries, "last_activity_at": t.get("last_activity_at"), "last_message": t.get("messages", [{}])[-1] if t.get("messages") else None}
        def filter_fields(thread, fields):
            t = thread.dict()
            return {field: t.get(field) for field in fields}
        try:
            threads = instagram_client.direct_threads(amount, selected_filter, thread_message_limit)
            if full: return {"success": True, "threads": [t.dict() for t in threads]}
            elif fields: return {"success": True, "threads": [filter_fields(t, fields) for t in threads]}
            else: return {"success": True, "threads": [thread_summary(t) for t in threads]}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def list_messages(thread_id: str, amount: int = 20) -> Dict[str, Any]:
    """Get messages from a specific Instagram Direct Message thread by thread ID, with an optional limit."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not thread_id: return {"success": False, "message": "Thread ID must be provided."}
        try:
            messages = instagram_client.direct_messages(thread_id, amount)
            return {"success": True, "messages": [m.dict() for m in messages]}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def mark_message_seen(thread_id: str, message_id: str) -> Dict[str, Any]:
    """Mark a message as seen in a direct message thread."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not thread_id or not message_id: return {"success": False, "message": "Both thread_id and message_id must be provided."}
        try:
            result = instagram_client.direct_message_seen(int(thread_id), int(message_id))
            return {"success": True, "message": "Message marked as seen."} if result else {"success": False, "message": "Failed to mark message as seen."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def list_pending_chats(amount: int = 20) -> Dict[str, Any]:
    """Get Instagram Direct Message threads (chats) from the user's pending inbox."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        try:
            threads = instagram_client.direct_pending_inbox(amount)
            return {"success": True, "threads": [t.dict() for t in threads]}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def search_threads(query: str) -> Dict[str, Any]:
    """Search Instagram Direct Message threads by username or keyword."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not query: return {"success": False, "message": "Query must be provided."}
        try:
            results = instagram_client.direct_search(query)
            return {"success": True, "results": [r.dict() for r in results]}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_thread_by_participants(user_ids: List[int]) -> Dict[str, Any]:
    """Get an Instagram Direct Message thread by participant user IDs."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not user_ids or not isinstance(user_ids, list): return {"success": False, "message": "user_ids must be a non-empty list of user IDs."}
        try:
            thread = instagram_client.direct_thread_by_participants(user_ids)
            return {"success": True, "thread": thread.dict()}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_thread_details(thread_id: str, amount: int = 20) -> Dict[str, Any]:
    """Get details and messages for a specific Instagram Direct Message thread by thread ID."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not thread_id: return {"success": False, "message": "Thread ID must be provided."}
        try:
            thread = instagram_client.direct_thread(thread_id, amount)
            return {"success": True, "thread": thread.dict()}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_id_from_username(username: str) -> Dict[str, Any]:
    """Get the Instagram user ID for a given username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            return {"success": True, "user_id": user_id} if user_id else {"success": False, "message": f"User '{username}' not found."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_username_from_user_id(user_id: str) -> Dict[str, Any]:
    """Get the Instagram username for a given user ID."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not user_id: return {"success": False, "message": "User ID must be provided."}
        try:
            username = instagram_client.username_from_user_id(user_id)
            return {"success": True, "username": username} if username else {"success": False, "message": f"User ID '{user_id}' not found."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_info(username: str) -> Dict[str, Any]:
    """Get detailed information about an Instagram user."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user = instagram_client.user_info_by_username(username)
            return {"success": True, "user_info": user.dict()} if user else {"success": False, "message": f"User '{username}' not found."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def check_user_online_status(usernames: List[str]) -> Dict[str, Any]:
    """Check the online status of Instagram users."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not usernames or not isinstance(usernames, list): return {"success": False, "message": "A list of usernames must be provided."}
        try:
            user_ids, username_to_id = [], {}
            for username in usernames:
                try:
                    user_id = instagram_client.user_id_from_username(username)
                    if user_id:
                        user_ids.append(int(user_id))
                        username_to_id[str(user_id)] = username
                except: continue
            if not user_ids: return {"success": False, "message": "No valid users found."}
            
            presence_data = instagram_client.direct_users_presence(user_ids)
            result = {username_to_id.get(user_id_str, f"user_{user_id_str}"): presence for user_id_str, presence in presence_data.items()}
            return {"success": True, "presence_data": result}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def search_users(query: str) -> Dict[str, Any]:
    """Search for Instagram users by name or username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not query: return {"success": False, "message": "Search query must be provided."}
        try:
            users = instagram_client.search_users(query)
            return {"success": True, "users": [u.dict() for u in users], "count": len(users)}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_stories(username: str) -> Dict[str, Any]:
    """Get Instagram stories from a user."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            stories = instagram_client.user_stories(user_id)
            return {"success": True, "stories": [s.dict() for s in stories], "count": len(stories)}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def like_media(media_url: str, like: bool = True) -> Dict[str, Any]:
    """Like or unlike an Instagram post."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not media_url: return {"success": False, "message": "Media URL must be provided."}
        try:
            media_pk = instagram_client.media_pk_from_url(media_url)
            if not media_pk: return {"success": False, "message": "Invalid media URL or post not found."}
            action = "liked" if like else "unliked"
            result = instagram_client.media_like(media_pk) if like else instagram_client.media_unlike(media_pk)
            return {"success": True, "message": f"Post {action} successfully."} if result else {"success": False, "message": f"Failed to {action.rstrip('d')} post."}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_followers(username: str, count: int = 20) -> Dict[str, Any]:
    """Get followers of an Instagram user."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            followers = instagram_client.user_followers(user_id, amount=count)
            return {"success": True, "followers": [f.dict() for f in followers.values()], "count": len(followers)}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_following(username: str, count: int = 20) -> Dict[str, Any]:
    """Get users that an Instagram user is following."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            following = instagram_client.user_following(user_id, amount=count)
            return {"success": True, "following": [f.dict() for f in following.values()], "count": len(following)}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)

@mcp.tool()
async def get_user_posts(username: str, count: int = 12) -> Dict[str, Any]:
    """Get recent posts from an Instagram user."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    def sync_op():
        if not username: return {"success": False, "message": "Username must be provided."}
        try:
            user_id = instagram_client.user_id_from_username(username)
            if not user_id: return {"success": False, "message": f"User '{username}' not found."}
            medias = instagram_client.user_medias(user_id, amount=count)
            return {"success": True, "posts": [m.dict() for m in medias], "count": len(medias)}
        except Exception as e: return {"success": False, "message": str(e)}
    return await asyncio.to_thread(sync_op)


# =============================================================================
# --- FIRECRAWL TOOLS ---
# =============================================================================

@mcp.tool()
async def scrape_url(url: str, formats: List[str] = ["markdown", "html"]) -> Dict[str, Any]:
    """Scrape a single URL using Firecrawl."""
    if not firecrawl_client:
        return {"success": False, "message": "Firecrawl client not initialized."}
    
    try:
        scrape_options = ScrapeOptions(formats=formats)
        result = firecrawl_client.scrape_url(url, scrape_options)
        return {
            "success": True,
            "data": result,
            "url": url
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def search_web(query: str, limit: int = 10, formats: List[str] = ["markdown"]) -> Dict[str, Any]:
    """Search the web using Firecrawl."""
    if not firecrawl_client:
        return {"success": False, "message": "Firecrawl client not initialized."}
    
    try:
        scrape_options = ScrapeOptions(formats=formats)
        results = firecrawl_client.search(query, limit=limit, scrape_options=scrape_options)
        return {
            "success": True,
            "data": results.data,
            "query": query,
            "count": len(results.data)
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def discover_instagram_influencers(hashtag: str, min_followers: int = 5000, limit: int = 20) -> Dict[str, Any]:
    """Discover Instagram influencers by hashtag using web scraping."""
    if not firecrawl_client:
        return {"success": False, "message": "Firecrawl client not initialized."}
    
    try:
        # Search for Instagram profiles mentioning the hashtag
        query = f'site:instagram.com "{hashtag}" influencer OR bio OR profile'
        search_results = firecrawl_client.search(
            query,
            limit=30,
            scrape_options=ScrapeOptions(formats=["links", "markdown"])
        )
        
        # Extract Instagram profile URLs
        profile_urls = set()
        for result in search_results.data:
            # Look for Instagram URLs in links
            for link in result.get("links", []):
                if re.match(r"https?://(www\.)?instagram\.com/[^/]+/?$", link):
                    profile_urls.add(link)
        
        candidates = []
        processed = 0
        
        for url in list(profile_urls)[:limit]:
            if processed >= limit:
                break
                
            try:
                username = url.rstrip("/").split("/")[-1]
                
                # Scrape the profile page
                profile_data = firecrawl_client.scrape_url(
                    url,
                    ScrapeOptions(formats=["markdown"])
                )
                
                content = profile_data.get("markdown", "")
                
                # Parse follower count (multiple patterns to catch different formats)
                follower_patterns = [
                    r'(\d[\d,\.KM]+)\s+[Ff]ollowers',
                    r'(\d[\d,\.KM]+)\s+[Ff]ollower',
                    r'[Ff]ollowers:\s*(\d[\d,\.KM]+)',
                ]
                
                followers = 0
                for pattern in follower_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        follower_str = match.group(1).upper()
                        # Convert K/M notation to numbers
                        if 'K' in follower_str:
                            followers = int(float(follower_str.replace('K', '').replace(',', '')) * 1000)
                        elif 'M' in follower_str:
                            followers = int(float(follower_str.replace('M', '').replace(',', '')) * 1000000)
                        else:
                            followers = int(follower_str.replace(',', ''))
                        break
                
                # Extract bio/description
                bio_match = re.search(r'bio[:\s]*([^\n]+)', content, re.IGNORECASE)
                bio = bio_match.group(1).strip() if bio_match else ""
                
                if followers >= min_followers:
                    candidates.append({
                        "username": username,
                        "url": url,
                        "followers": followers,
                        "bio": bio,
                        "hashtag_relevance": hashtag.lower() in content.lower()
                    })
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"Failed to process {url}: {e}")
                continue
        
        # Sort by follower count
        candidates.sort(key=lambda x: x["followers"], reverse=True)
        
        return {
            "success": True,
            "hashtag": hashtag,
            "candidates": candidates,
            "total_found": len(candidates),
            "search_query": query
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def run_influencer_campaign(hashtag: str, message_template: str, min_followers: int = 5000, max_contacts: int = 10) -> Dict[str, Any]:
    """Discover influencers and send them personalized messages."""
    if not firecrawl_client or not instagram_client:
        return {"success": False, "message": "Firecrawl or Instagram client not initialized."}
    
    try:
        # First, discover influencers
        discovery_result = await discover_instagram_influencers(hashtag, min_followers, max_contacts * 2)
        
        if not discovery_result["success"]:
            return discovery_result
        
        candidates = discovery_result["candidates"][:max_contacts]
        
        # Send messages
        sent_messages = []
        failed_messages = []
        
        for candidate in candidates:
            try:
                # Personalize the message
                personalized_message = message_template.format(
                    username=candidate["username"],
                    hashtag=hashtag,
                    followers=candidate["followers"]
                )
                
                # Send message using existing Instagram tool
                result = await send_message(candidate["username"], personalized_message)
                
                if result["success"]:
                    sent_messages.append({
                        "username": candidate["username"],
                        "message": personalized_message,
                        "dm_id": result.get("direct_message_id")
                    })
                else:
                    failed_messages.append({
                        "username": candidate["username"],
                        "error": result["message"]
                    })
                    
                # Rate limiting - wait between messages
                await asyncio.sleep(2)
                
            except Exception as e:
                failed_messages.append({
                    "username": candidate["username"],
                    "error": str(e)
                })
        
        return {
            "success": True,
            "hashtag": hashtag,
            "sent_count": len(sent_messages),
            "failed_count": len(failed_messages),
            "sent_messages": sent_messages,
            "failed_messages": failed_messages,
            "total_candidates": len(candidates)
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}

async def perform_twitter_login():
    """An async function dedicated to logging into Twitter."""
    global twitter_client
    creds = (os.getenv("TWITTER_USERNAME"), os.getenv("TWITTER_EMAIL"), os.getenv("TWITTER_PASSWORD"))
    
    if not all(creds):
        logger.warning("Twitter credentials not found. Skipping Twitter login.")
        print("❌ Twitter credentials missing", file=sys.stderr)
        return
    
    logger.info("Attempting to login to Twitter...")
    print(f"🔄 Attempting Twitter login for {creds[0]}", file=sys.stderr)
    
    twitter_client = TwitterClient('en-US')
    try:
        if COOKIES_PATH.exists():
            logger.info("Loading Twitter cookies from file.")
            twitter_client.load_cookies(COOKIES_PATH)
            print("✅ Twitter cookies loaded", file=sys.stderr)
        else:
            logger.info("No Twitter cookies found, performing fresh login.")
            print("🔄 Performing fresh Twitter login...", file=sys.stderr)
            await twitter_client.login(auth_info_1=creds[0], auth_info_2=creds[1], password=creds[2])
            twitter_client.save_cookies(COOKIES_PATH)
            logger.info(f"Saved Twitter cookies to {COOKIES_PATH}")
            print("✅ Twitter login successful, cookies saved", file=sys.stderr)
        
        # Test the connection
        user_info = await twitter_client.get_user_by_screen_name(creds[0])
        print(f"✅ Twitter authenticated as @{user_info.screen_name}", file=sys.stderr)
        logger.info("Successfully logged in to Twitter.")
        
    except Exception as e:
        logger.error(f"Failed to login to Twitter: {e}")
        print(f"❌ Twitter login failed: {e}", file=sys.stderr)
        twitter_client = None
# =============================================================================
# --- UPDATE MAIN FUNCTION ---
# =============================================================================

def main():
    """Main function to handle logins and run the server."""
    global instagram_client, firecrawl_client
    
    # Initialize Firecrawl
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    if firecrawl_api_key:
        try:
            firecrawl_client = FirecrawlApp(api_key=firecrawl_api_key)
            logger.info("Firecrawl client initialized successfully.")
            print("✅ Firecrawl initialized", file=sys.stderr)
        except Exception as e:
            logger.error(f"Failed to initialize Firecrawl: {e}")
            print(f"❌ Firecrawl initialization failed: {e}", file=sys.stderr)
    else:
        logger.warning("Firecrawl API key not found. Firecrawl features will be disabled.")
        print("⚠️ Firecrawl API key missing", file=sys.stderr)
    
    # Instagram login (existing code)
    creds = (os.getenv("INSTAGRAM_USERNAME"), os.getenv("INSTAGRAM_PASSWORD"))
    if all(creds):
        logger.info("Attempting to login to Instagram...")
        print("🔄 Attempting Instagram login...", file=sys.stderr)
        instagram_client = InstagramClient()
        try:
            instagram_client.login(creds[0], creds[1])
            logger.info("Successfully logged in to Instagram.")
            print("✅ Instagram login successful", file=sys.stderr)
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            print(f"❌ Instagram login failed: {e}", file=sys.stderr)
            instagram_client = None
    else:
        logger.warning("Instagram credentials not found. Skipping Instagram login.")
        print("⚠️ Instagram credentials missing", file=sys.stderr)

    # # Run the async part of the login
    # asyncio.run(perform_twitter_login())

    # Check available services
    available_services = []
    if instagram_client:
        available_services.append("Instagram")
    if twitter_client:
        available_services.append("Twitter")
    if firecrawl_client:
        available_services.append("Firecrawl")

    if not available_services:
        logger.error("Could not initialize any service. Shutting down.")
        print("❌ No services available - shutting down", file=sys.stderr)
        return
        
    logger.info(f"Starting unified MCP server with: {', '.join(available_services)}")
    print(f"🚀 MCP server starting with: {', '.join(available_services)}", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()