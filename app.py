#Copyright @ISmartCoder
#Updates Channel https://t.me/TheSmartDev
import asyncio
import logging
import os
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, AuthKeyPermEmptyError, SessionPasswordNeededError, PersistentTimestampEmptyError
from telethon import functions, types
from uuid import uuid4
import aiohttp
from datetime import datetime

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logger.info("Using uvloop for better performance")
except ImportError:
    logger.warning("uvloop not available, using default event loop")

class BotInfoModel(BaseModel):
    first_name: str
    id: int
    username: Optional[str] = None

class ChatModel(BaseModel):
    id: int
    members_count: Optional[int] = None
    title: str
    type: str
    username: Optional[str] = None

class UserModel(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_premium: bool = False

class BotDataResponse(BaseModel):
    bot_info: BotInfoModel
    chats: List[ChatModel]
    users: List[UserModel]
    total_chats: int = Field(..., description="Total number of chats")
    total_users: int = Field(..., description="Total number of users")
    processing_time: float = Field(..., description="Processing time in seconds")

class ClientManager:
    def __init__(self):
        self.clients: Dict[str, TelegramClient] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.global_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def get_client(self, bot_token: str, api_id: int, api_hash: str) -> TelegramClient:
        async with self.global_lock:
            if bot_token not in self.locks:
                self.locks[bot_token] = asyncio.Lock()
        async with self.locks[bot_token]:
            if bot_token in self.clients:
                client = self.clients[bot_token]
                try:
                    if client.is_connected():
                        return client
                    else:
                        await client.disconnect()
                        del self.clients[bot_token]
                except Exception as e:
                    logger.warning(f"Client connection issue: {e}")
            if bot_token in self.clients:
                del self.clients[bot_token]
            session_name = f"bot_{uuid4().hex[:8]}"
            client = TelegramClient(
                session=session_name,
                api_id=api_id,
                api_hash=api_hash,
                base_logger=logger
            )
            try:
                await asyncio.wait_for(client.start(bot_token=bot_token), timeout=30.0)
                async with self.global_lock:
                    self.clients[bot_token] = client
                logger.info(f"Client created successfully for token: {bot_token[:10]}...")
                return client
            except Exception as e:
                logger.error(f"Failed to create client: {e}")
                try:
                    await client.disconnect()
                except:
                    pass
                raise HTTPException(status_code=400, detail=f"Failed to connect to Telegram: {str(e)}")

    async def cleanup_client(self, bot_token: str):
        try:
            async with self.global_lock:
                if bot_token in self.clients:
                    client = self.clients[bot_token]
                    try:
                        if client.is_connected():
                            await asyncio.wait_for(client.disconnect(), timeout=10.0)
                    except Exception as e:
                        logger.warning(f"Error stopping client: {e}")
                    finally:
                        del self.clients[bot_token]
                if bot_token in self.locks:
                    del self.locks[bot_token]
                logger.info(f"Client cleaned up for token: {bot_token[:10]}...")
        except Exception as e:
            logger.error(f"Error cleaning up client {bot_token[:10]}...: {e}")

    async def shutdown(self):
        logger.info("Shutting down client manager...")
        try:
            async with self.global_lock:
                for bot_token in list(self.clients.keys()):
                    await self.cleanup_client(bot_token)
                if self._session and not self._session.closed:
                    await self._session.close()
                self.executor.shutdown(wait=True)
            logger.info("Client manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

client_manager = ClientManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Enhanced Telegram Users API...")
    try:
        yield
    finally:
        await client_manager.shutdown()
        logger.info("API shutdown complete")

app = FastAPI(
    title="Enhanced Telegram Users API",
    description="High-performance async API for Telegram bot data with improved concurrency",
    version="2.1.0",
    lifespan=lifespan
)

def normalize_chat_type(raw_type: str) -> str:
    type_map = {
        "chat": "group",
        "channel": "channel",
        "chatforbidden": "group",
        "channelforbidden": "channel",
        "user": "private"
    }
    return type_map.get(raw_type.lower(), raw_type.lower())

def merge_chat_data(existing: Optional[ChatModel], new: ChatModel) -> ChatModel:
    if not existing:
        return new
    return ChatModel(
        id=existing.id,
        members_count=new.members_count if new.members_count is not None else existing.members_count,
        title=new.title if new.title and new.title != "Unknown" else existing.title,
        type=new.type,
        username=new.username if new.username else existing.username
    )

async def fetch_chat_participants(client: TelegramClient, chat_id: int, chat_type: str, chat: ChatModel) -> List[UserModel]:
    users = []
    try:
        if chat_type in ["group", "channel"]:
            if chat.members_count is not None and chat.members_count > 5000:
                logger.info(f"Skipping large chat {chat_id} with {chat.members_count} members to optimize performance")
                return []
            async for participant in client.iter_participants(chat_id, limit=5000):
                users.append(UserModel(
                    id=participant.id,
                    first_name=participant.first_name,
                    last_name=participant.last_name,
                    username=participant.username,
                    is_premium=participant.premium
                ))
    except Exception as e:
        logger.warning(f"Failed to fetch participants for chat {chat_id}: {str(e)}")
    return users

async def get_chats_and_users_fast(client: TelegramClient) -> Tuple[List[ChatModel], List[UserModel]]:
    chats: Dict[int, ChatModel] = {}
    users: Dict[int, UserModel] = {}
    inaccessible_chats = set()
    batch_count = 0
    try:
        state = await client.get_state()
        custom_pts = state.pts
        custom_date = state.date
        custom_qts = state.qts
        logger.info(f"Initialized state: pts={custom_pts}, qts={custom_qts}, date={custom_date}")
    except Exception as e:
        logger.warning(f"Failed to get initial state: {e}, using fallback values")
        custom_pts = 1
        custom_date = datetime.now()
        custom_qts = 1
    start_time = time.time()
    max_duration = 600
    max_batches = 1000
    no_data_count = 0
    max_no_data = 5
    try:
        while time.time() - start_time < max_duration and batch_count < max_batches:
            try:
                diff = await asyncio.wait_for(
                    client(functions.updates.GetDifferenceRequest(
                        pts=custom_pts,
                        date=custom_date,
                        qts=custom_qts,
                        pts_limit=10000,
                        qts_limit=10000
                    )),
                    timeout=60.0
                )
                if isinstance(diff, types.updates.DifferenceTooLong):
                    logger.warning(f"Difference too long, updating pts to {diff.pts}")
                    custom_pts = diff.pts
                    continue
                if isinstance(diff, types.updates.DifferenceEmpty):
                    logger.info("Difference empty, no new updates")
                    break
                batch_users = []
                batch_chats = []
                for user in getattr(diff, 'users', []):
                    if user.id not in users:
                        users[user.id] = UserModel(
                            id=user.id,
                            first_name=getattr(user, 'first_name', None),
                            last_name=getattr(user, 'last_name', None),
                            username=getattr(user, 'username', None),
                            is_premium=getattr(user, 'premium', False)
                        )
                        batch_users.append({
                            "id": user.id,
                            "first_name": getattr(user, 'first_name', None),
                            "username": getattr(user, 'username', None)
                        })
                for chat in getattr(diff, 'chats', []):
                    if chat.id not in chats and chat.id not in inaccessible_chats:
                        chat_class_name = chat.__class__.__name__.lower()
                        if chat_class_name in ["chatforbidden", "channelforbidden"]:
                            inaccessible_chats.add(chat.id)
                            continue
                        chat_type = normalize_chat_type(chat_class_name)
                        chat_data = ChatModel(
                            id=chat.id,
                            members_count=getattr(chat, 'participants_count', None),
                            title=getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown",
                            type=chat_type,
                            username=getattr(chat, 'username', None)
                        )
                        chats[chat.id] = merge_chat_data(chats.get(chat.id), chat_data)
                        batch_chats.append({
                            "id": chat_data.id,
                            "members_count": chat_data.members_count,
                            "title": chat_data.title,
                            "type": chat_data.type,
                            "username": chat_data.username
                        })
                for update in getattr(diff, 'new_messages', []):
                    if hasattr(update, 'message') and hasattr(update.message, 'peer_id'):
                        try:
                            chat = await client.get_entity(update.message.peer_id)
                            if chat.id not in chats and chat.id not in inaccessible_chats:
                                chat_class_name = chat.__class__.__name__.lower()
                                if chat_class_name in ["chatforbidden", "channelforbidden"]:
                                    inaccessible_chats.add(chat.id)
                                    continue
                                chat_type = normalize_chat_type(chat_class_name)
                                chat_data = ChatModel(
                                    id=chat.id,
                                    members_count=getattr(chat, 'participants_count', None),
                                    title=getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown",
                                    type=chat_type,
                                    username=getattr(chat, 'username', None)
                                )
                                chats[chat.id] = merge_chat_data(chats.get(chat.id), chat_data)
                                batch_chats.append({
                                    "id": chat_data.id,
                                    "members_count": chat_data.members_count,
                                    "title": chat_data.title,
                                    "type": chat_data.type,
                                    "username": chat_data.username
                                })
                        except Exception as e:
                            logger.warning(f"Failed to process message update: {str(e)}")
                if batch_users or batch_chats:
                    logger.info(f"Batch {batch_count}:")
                    logger.info(f" Users fetched: {len(batch_users)}")
                    if batch_users:
                        logger.debug(f" Users: {[user['id'] for user in batch_users]}")
                    logger.info(f" Chats fetched: {len(batch_chats)}")
                    if batch_chats:
                        logger.debug(f" Chats: {[chat['id'] for chat in batch_chats]}")
                    if inaccessible_chats:
                        logger.info(f" Inaccessible chats: {len(inaccessible_chats)} IDs skipped")
                    no_data_count = 0
                else:
                    logger.info(f"Batch {batch_count}: Skipped (no new users or chats)")
                    no_data_count += 1
                    if no_data_count >= max_no_data:
                        logger.info("No new data for multiple batches, stopping iteration")
                        break
                batch_count += 1
                if isinstance(diff, types.updates.DifferenceSlice):
                    custom_pts = diff.intermediate_state.pts
                    custom_date = diff.intermediate_state.date
                    custom_qts = diff.intermediate_state.qts
                elif isinstance(diff, types.updates.Difference):
                    logger.info("Reached final difference, stopping iteration")
                    break
                else:
                    logger.warning(f"Unknown diff type: {type(diff)}")
                    break
                await asyncio.sleep(0.05)
            except PersistentTimestampEmptyError as e:
                logger.error(f"Persistent timestamp empty error: {e}")
                try:
                    state = await client.get_state()
                    custom_pts = state.pts
                    custom_date = state.date
                    custom_qts = state.qts
                    logger.info(f"Recovered state: pts={custom_pts}, qts={custom_qts}, date={custom_date}")
                    continue
                except Exception as state_e:
                    logger.error(f"Failed to recover state: {state_e}")
                    break
            except asyncio.TimeoutError:
                logger.warning("GetDifference timeout, continuing with collected data")
                break
            except FloodWaitError as fw:
                if fw.seconds > 30:
                    logger.warning(f"FloodWait too long: {fw.seconds}s, breaking")
                    break
                logger.info(f"FloodWait: {fw.seconds}s")
                await asyncio.sleep(fw.seconds)
            except Exception as e:
                logger.error(f"Error in iteration {batch_count}: {str(e)}")
                if batch_count > max_batches:
                    logger.warning("Reached max batches, stopping iteration")
                    break
                await asyncio.sleep(1)
        if time.time() - start_time >= max_duration:
            logger.warning("Reached timeout, proceeding to fetch chat participants")
        logger.info(f"Fetching participants from {len(chats)} chats to ensure all users are captured")
        tasks = []
        for chat_id, chat in chats.items():
            tasks.append(fetch_chat_participants(client, chat_id, chat.type, chat))
        for i in range(0, len(tasks), 10):
            batch_tasks = tasks[i:i+10]
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for additional_users in results:
                if isinstance(additional_users, list):
                    for user in additional_users:
                        if user.id not in users:
                            users[user.id] = user
                            logger.debug(f"Added user {user.id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Major error fetching chats and users: {str(e)}")
    logger.info(f"Collected {len(chats)} chats and {len(users)} users in {batch_count} batches")
    return list(chats.values()), list(users.values())

@app.get("/")
async def get_api_info():
    return {
        "api_name": "Enhanced Telegram Users API",
        "version": "2.1.0",
        "status": "running",
        "description": "High-performance API for Telegram bot data with improved concurrency",
        "owners": [
            {"username": "@ISmartCoder"},
            {"username": "@theSmartDev"}
        ],
        "endpoints": [
            {
                "path": "/tgusers",
                "method": "GET",
                "description": "Fetch bot data including bot info, chats, and users",
                "parameters": [
                    {
                        "name": "token",
                        "type": "string",
                        "required": True,
                        "description": "Telegram Bot Token"
                    }
                ]
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check endpoint"
            },
            {
                "path": "/docs",
                "method": "GET",
                "description": "Get interactive API documentation"
            }
        ],
        "contact": "Contact @ISmartCoder or @theSmartDev for support"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_clients": len(client_manager.clients)
    }

@app.get("/tgusers", response_model=BotDataResponse)
async def get_bot_data_fast(
    background_tasks: BackgroundTasks,
    token: str = Query(..., description="Telegram Bot Token", min_length=10)
):
    start_time = time.time()
    if not token or len(token.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid bot token format")
    try:
        logger.info(f"Processing request for token: {token[:10]}...")
        client = await client_manager.get_client(
            bot_token=token.strip(),
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
        )
        try:
            bot_info_task = asyncio.create_task(
                asyncio.wait_for(client.get_me(), timeout=15.0)
            )
            chats_users_task = asyncio.create_task(
                asyncio.wait_for(get_chats_and_users_fast(client), timeout=600.0)
            )
            results = await asyncio.gather(
                bot_info_task,
                chats_users_task,
                return_exceptions=True
            )
            me = results[0]
            chats_users = results[1]
            if isinstance(me, Exception):
                logger.error(f"Error getting bot info: {me}")
                raise me
            if isinstance(chats_users, Exception):
                logger.warning(f"Error getting chats/users: {chats_users}")
                chats, users = [], []
            else:
                chats, users = chats_users
            if not isinstance(chats, list):
                chats = []
            if not isinstance(users, list):
                users = []
            bot_info = BotInfoModel(
                first_name=me.first_name or "Unknown",
                id=me.id,
                username=me.username
            )
            processing_time = time.time() - start_time
            response = BotDataResponse(
                bot_info=bot_info,
                chats=chats,
                users=users,
                total_chats=len(chats),
                total_users=len(users),
                processing_time=round(processing_time, 3)
            )
            logger.info(f"Request completed in {processing_time:.3f}s - Chats: {len(chats)}, Users: {len(users)}")
            background_tasks.add_task(client_manager.cleanup_client, token.strip())
            return response
        except asyncio.TimeoutError:
            logger.error("Request timeout")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=408, detail="Request timeout - try again")
        except (AuthKeyPermEmptyError, SessionPasswordNeededError) as e:
            logger.error(f"Authentication error: {e}")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=401, detail="Invalid bot token or bot deactivated")
        except HTTPException:
            raise
        except RPCError as e:
            logger.error(f"Telegram API error: {e}")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=400, detail=f"Telegram API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await client_manager.cleanup_client(token.strip())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "__main__:app",
        host=host,
        port=port,
        workers=1,
        loop="uvloop" if 'uvloop' in globals() else "asyncio",
        access_log=True,
        reload=False,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )