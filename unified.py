
import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

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
# We will initialize these clients in our main async function
instagram_client: Optional[InstagramClient] = None
twitter_client: Optional[TwitterClient] = None

# Twitter cookie path (from luniakunal's script)
COOKIES_PATH = Path('./twitter_cookies.json') # Store cookies in the current directory

# =============================================================================
# --- TWITTER TOOLS (FROM LUNIAKUNAL + NEW DM TOOLS) ---
# =============================================================================

def get_tweet_data(tweet: twikit.Tweet) -> Dict:
    """Helper function to convert a twikit Tweet object into a clean dictionary."""
    try:
        return {
            'id': tweet.id,
            'text': tweet.text,
            'username': tweet.user.screen_name,
            'user_id': tweet.user.id,
            'created_at': tweet.created_at,
            'likes': tweet.favorite_count,
            'replies': tweet.reply_count,
            'retweets': tweet.retweet_count,
        }
    except Exception as e:
        logger.error(f"Error processing tweet data: {e}")
        return {'error': str(e)}

@mcp.tool()
async def get_tweets(query: str, sort_by: str = 'Latest', count: int = 20) -> List[dict]:
    """Search twitter with a query. Sort by 'Top' or 'Latest'."""
    if not twitter_client: return [{"error": "Twitter client not initialized. Please login."}]
    try:
        tweets = await twitter_client.search_tweet(query, sort_by, count=count)
        return [get_tweet_data(tweet) for tweet in tweets]
    except Exception as e:
        logger.error(f"Error during tweet retrieval: {e}")
        return [{"error": str(e)}]

@mcp.tool()
async def get_user_tweets(username: str, tweet_type: str = 'Tweets', count: int = 10) -> List[dict]:
    """Get tweets from a specific user's timeline."""
    if not twitter_client: return [{"error": "Twitter client not initialized."}]
    try:
        username = username.lstrip('@')
        user = await twitter_client.get_user_by_screen_name(username)
        tweets = await twitter_client.get_user_tweets(user.id, tweet_type=tweet_type, count=count)
        return [get_tweet_data(tweet) for tweet in tweets]
    except Exception as e:
        logger.error(f"Failed to get user tweets: {e}")
        return [{"error": str(e)}]

@mcp.tool()
async def post_tweet(text: str, media_paths: Optional[List[str]] = None) -> str:
    """Post a tweet with optional media."""
    if not twitter_client: return "Error: Twitter client not initialized."
    try:
        media_ids = []
        if media_paths:
            for path in media_paths:
                media_id = await twitter_client.upload_media(path, wait_for_completion=True)
                media_ids.append(media_id)
        tweet = await twitter_client.create_tweet(text=text, media_ids=media_ids or None)
        return f"Successfully posted tweet: {tweet.id}"
    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        return f"Failed to post tweet: {e}"

@mcp.tool()
async def send_twitter_dm(username: str, text: str) -> Dict[str, Any]:
    """Sends a Direct Message to a user on Twitter."""
    if not twitter_client: return {"success": False, "message": "Twitter client not initialized."}
    if not username or not text: return {"success": False, "message": "Username and text must be provided."}
        
    logger.info(f"Attempting to send DM to {username}")
    try:
        user = await twitter_client.get_user_by_screen_name(username.lstrip('@'))
        if not user: return {"success": False, "message": f"Could not find Twitter user: {username}"}

        await twitter_client.create_dm(user.id, text)
        
        logger.info(f"Successfully sent DM to {username}")
        return {"success": True, "message": f"DM successfully sent to @{user.screen_name}."}
    except Exception as e:
        logger.error(f"Failed to send Twitter DM: {e}")
        return {"success": False, "message": f"An error occurred: {e}"}

@mcp.tool()
async def list_twitter_dms(count: int = 20) -> Dict[str, Any]:
    """Lists the most recent Twitter DM conversations."""
    if not twitter_client: return {"success": False, "message": "Twitter client not initialized."}
    logger.info("Fetching recent Twitter DMs...")
    try:
        inbox = await twitter_client.get_dm_inbox(count=count)
        
        conversations = []
        for conv in inbox.conversations:
            participants = [p.screen_name for p in conv.participants if p.id != twitter_client.user.id]
            last_message = conv.messages[0].text if conv.messages else "[No messages]"
            
            conversations.append({
                "conversation_id": conv.id,
                "participants": participants,
                "last_message": last_message,
                "timestamp": conv.messages[0].created_at if conv.messages else ""
            })
        return {"success": True, "conversations": conversations}
    except Exception as e:
        logger.error(f"Failed to list Twitter DMs: {e}")
        return {"success": False, "message": f"An error occurred: {e}"}

# =============================================================================
# --- INSTAGRAM TOOLS (ADAPTED FOR ASYNC) ---
# =============================================================================

@mcp.tool()
async def send_instagram_dm(username: str, message: str) -> Dict[str, Any]:
    """Send an Instagram direct message to a user by username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    if not username or not message: return {"success": False, "message": "Username and message must be provided."}
        
    def sync_send_dm():
        try:
            user_id = instagram_client.user_id_from_username(username)
            dm = instagram_client.direct_send(message, [user_id])
            return {"success": True, "message": "Message sent to user."} if dm else {"success": False, "message": "Failed to send message."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    return await asyncio.to_thread(sync_send_dm)

@mcp.tool()
async def send_instagram_photo(username: str, photo_path: str) -> Dict[str, Any]:
    """Send a photo via Instagram direct message to a user by username."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}
    if not os.path.exists(photo_path): return {"success": False, "message": f"Photo file not found: {photo_path}"}

    def sync_send_photo():
        try:
            user_id = instagram_client.user_id_from_username(username)
            result = instagram_client.direct_send_photo(Path(photo_path), [user_id])
            return {"success": True, "message": "Photo sent successfully."} if result else {"success": False, "message": "Failed to send photo."}
        except Exception as e:
            return {"success": False, "message": str(e)}
            
    return await asyncio.to_thread(sync_send_photo)

@mcp.tool()
async def list_instagram_chats(amount: int = 20) -> Dict[str, Any]:
    """Get Instagram Direct Message threads (chats) from the user's account."""
    if not instagram_client: return {"success": False, "message": "Instagram client not initialized."}

    def sync_list_chats():
        try:
            threads = instagram_client.direct_threads(amount)
            return {"success": True, "threads": [t.dict() for t in threads]}
        except Exception as e:
            return {"success": False, "message": str(e)}

    return await asyncio.to_thread(sync_list_chats)

# =============================================================================
# --- MAIN EXECUTION AND LOGIN LOGIC ---
# =============================================================================

async def main():
    """Main function to handle logins and run the server."""
    global instagram_client, twitter_client

    # 1. Login to Instagram
    insta_user = os.getenv("INSTAGRAM_USERNAME")
    insta_pass = os.getenv("INSTAGRAM_PASSWORD")
    if insta_user and insta_pass:
        logger.info("Attempting to login to Instagram...")
        instagram_client = InstagramClient()
        try:
            await asyncio.to_thread(instagram_client.login, insta_user, insta_pass)
            logger.info("Successfully logged in to Instagram.")
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            instagram_client = None
    else:
        logger.warning("Instagram credentials not found in .env file. Skipping login.")

    # 2. Login to Twitter
    twitter_user = os.getenv("TWITTER_USERNAME")
    twitter_email = os.getenv("TWITTER_EMAIL")
    twitter_pass = os.getenv("TWITTER_PASSWORD")
    if twitter_user and twitter_email and twitter_pass:
        logger.info("Attempting to login to Twitter...")
        twitter_client = TwitterClient('en-US')
        try:
            if COOKIES_PATH.exists():
                logger.info("Loading Twitter cookies from file.")
                twitter_client.load_cookies(COOKIES_PATH)
            else:
                logger.info("No Twitter cookies found, performing fresh login.")
                await twitter_client.login(
                    auth_info_1=twitter_user,
                    auth_info_2=twitter_email,
                    password=twitter_pass
                )
                twitter_client.save_cookies(COOKIES_PATH)
                logger.info(f"Saved Twitter cookies to {COOKIES_PATH}")
            logger.info("Successfully logged in to Twitter.")
        except Exception as e:
            logger.error(f"Failed to login to Twitter: {e}")
            twitter_client = None
    else:
        logger.warning("Twitter credentials not found in .env file. Skipping login.")

    # 3. Run the MCP Server
    if not instagram_client and not twitter_client:
        logger.error("Could not log in to any service. Shutting down.")
        return
        
    logger.info("Starting unified MCP server...")
    await mcp.run()

if __name__ == "__main__":
    asyncio.run(main())
