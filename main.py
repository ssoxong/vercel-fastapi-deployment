from time import time
from fastapi import FastAPI, __version__
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

html = f"""
<!DOCTYPE html>
<html>
    <head>
        <title>FastAPI on Vercel</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
    </head>
    <body>
        <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
            <h1>Hello from FastAPI@{__version__}</h1>
            <ul>
                <li><a href="/docs">/docs</a></li>
                <li><a href="/redoc">/redoc</a></li>
            </ul>
            <p>Powered by <a href="https://vercel.com" target="_blank">Vercel</a></p>
        </div>
    </body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(html)

@app.get('/ping')
async def hello():
    return {'res': 'pong', 'version': __version__, "time": time()}

from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, DateTime, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.sql import func
import requests
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://ssoxong:O510tE7q0JlMSaWV@cluster0.3x6ex.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.dkbe  # 'forum'은 데이터베이스 이름입니다.

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
class Comment(BaseModel):
    id: str = Field(alias="_id")
    content: str
    post_id: str

class Post(BaseModel):
    id: str = Field(alias="_id")
    title: str
    content: str
    comments: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)

class PostCreate(BaseModel):
    title: str
    content: str

class CommentCreate(BaseModel):
    content: str

# DB 의존성
def get_db():
    return db

class PostResponse(BaseModel):
    id: int 
    title: str
    content: str
    created_at: datetime

@app.post("/posts/", response_model=str)
async def create_post(post: PostCreate, db=Depends(get_db)):
    post_dict = post.dict()
    post_dict['created_at'] = datetime.now()
    result = await db.posts.insert_one(post_dict)
    return str(result.inserted_id)

@app.get("/posts/", response_model=List[Post])
async def read_posts(db=Depends(get_db)):
    posts = await db.posts.find().sort("created_at", -1).to_list(100)
    # object id 를 string 으로 변환
    for post in posts:
        post["_id"] = str(post["_id"])
    return posts

@app.get("/posts/{post_id}", response_model=Post)
async def read_post(post_id: str, db=Depends(get_db)):
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if post:
        post["_id"] = str(post["_id"])
        return post
    else:
        raise HTTPException(status_code=404, detail="Post not found")

@app.post("/posts/{post_id}/comments/", response_model=str)
async def add_comment_to_post(post_id: str, comment: CommentCreate, db=Depends(get_db)):
    comment_dict = comment.dict()
    comment_dict['post_id'] = post_id
    result = await db.comments.insert_one(comment_dict)
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if post:
        if "comments" not in post:
            post['comments'] = []
        post['comments'].append(result.inserted_id)
        await db.posts.update_one({"_id": ObjectId(post_id)}, {"$set": post})

    return str(result.inserted_id)

@app.get("/posts/{post_id}/comments/", response_model=List[Comment])
async def get_comments(post_id: str, db=Depends(get_db)):
    comments = await db.comments.find({"post_id": post_id}).to_list(100)
    # object id 를 string 으로 변환
    for comment in comments:
        comment["_id"] = str(comment["_id"])
    return comments

@app.get("/school-meals/{atpt_code}/{school_code}/{date}", response_class=PlainTextResponse)
async def get_school_meals(atpt_code:str, school_code: str, date: str):
    api_key = os.getenv("LUNCH_API")
    url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={api_key}&ATPT_OFCDC_SC_CODE={atpt_code}&SD_SCHUL_CODE={school_code}&MLSV_YMD={date}"
    response = requests.get(url)
    if response.status_code == 200:
        return Response(content=response.text, media_type="application/xml")
    else:
        raise HTTPException(status_code=404, detail="Data not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
