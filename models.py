from sqlalchemy import (
    Table,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Boolean,
    ForeignKey,
)

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    backref
)

from sqlalchemy.sql import (
    func,
    expression
)

from sqlalchemy.ext.declarative import declarative_base

DBSession = scoped_session(sessionmaker(expire_on_commit=False))
Base = declarative_base()


# TODO __user_tablename__ = 'user' etc
tweet_note_assc = Table('tweet_note_association', Base.metadata,
                        Column('note_id', Integer, ForeignKey('note.id', ondelete='CASCADE')),
                        Column('tweet_id', BigInteger, ForeignKey('tweet.id', ondelete='CASCADE'))
                        )

category_note_assc = Table('category_note_association', Base.metadata,
                           Column('note_id', Integer, ForeignKey('note.id', ondelete='CASCADE')),
                           Column('category_id', Integer, ForeignKey('category.id', ondelete='CASCADE'))
                           )


class Tweet(Base):
    __tablename__ = 'tweet'
    id = Column(BigInteger, primary_key=True)
    url = Column(String(10000))

    text = Column(String(10000))

    # image


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String(10000))

    created_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'))
    # created_by = relationship("User")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Note(Base):
    __tablename__ = 'note'
    id = Column(Integer, primary_key=True)
    text = Column(String(10000))

    is_tweet = Column(Boolean, server_default=expression.false())

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    created_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'))

    tweets = relationship(Tweet, secondary=tweet_note_assc, backref=backref('tweet', lazy='dynamic'))
    categories = relationship(Category, secondary=category_note_assc, backref=backref('category', lazy='dynamic'))
    # created_by = relationship("User")

    # users_mentioned = Column(Integer, ForeignKey('user.id'))


class User(Base):
    __tablename__ = 'user'
    id = Column(BigInteger, primary_key=True)
    email = Column(String(256))
    # TODO Insert twitter user info here

    notes = relationship(Note, backref="created_by")
    categories = relationship(Category, backref="created_by")
