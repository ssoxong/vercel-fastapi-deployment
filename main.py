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


load_dotenv()


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 설정
DATABASE_URL = "sqlite:///./forum.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 모델 정의
class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True)
    content = Column(Text, nullable=False)
    comments = relationship("Comment", back_populates="post")
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성 날짜 추가


class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(255), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'))
    post = relationship("Post", back_populates="comments")

Base.metadata.create_all(bind=engine)

# 스키마 정의
class PostCreate(BaseModel):
    title: str
    content: str

class CommentCreate(BaseModel):
    content: str

# DB 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/posts/", response_model=int)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(title=post.title, content=post.content)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post.id

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

@app.get("/posts/", response_model=list[PostResponse])
def read_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.created_at.desc()).all()  # 최신순으로 정렬

@app.get("/posts/{post_id}", response_model=PostCreate)
def read_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.post("/posts/{post_id}/comments/", response_model=int)
def add_comment_to_post(post_id: int, comment: CommentCreate, db: Session = Depends(get_db)):
    db_comment = Comment(content=comment.content, post_id=post_id)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment.id

@app.get("/posts/{post_id}/comments/", response_model=list[CommentCreate])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
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
