import os
from sqlalchemy import Column, DateTime, Integer, String, create_engine, desc
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()


class BoardPosition(Base):
    __tablename__ = "BoardPosition"
    # нужен первичный ключ
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.now())
    x = Column(Integer)
    y = Column(Integer)

    def to_dict(self) -> dict:
        res = {
            # "date": datetime.strftime(self.time, r"%Y:%m:%d %H:%M"),
            "x" : self.x,
            "y" : self.y
        }
        return res


CUR_DIR = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(CUR_DIR, "data.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.drop_all(engine) 
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def get_last_pos():
    session.query(BoardPosition).order_by(desc(BoardPosition.time)).first()
