#!/usr/local/bin/python3
import sqlalchemy
import logging
import dateutil.parser
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, validates

Base = declarative_base()
db = sqlalchemy.create_engine('sqlite:///fb.sqlite')

place_topic = sqlalchemy.Table(
    'Place_Topic', Base.metadata,
    sqlalchemy.Column('place_id', sqlalchemy.String,
                      sqlalchemy.ForeignKey('Place.id')),
    sqlalchemy.Column('topic_id', sqlalchemy.String,
                      sqlalchemy.ForeignKey('Topic.id'))
)


class Topic(Base):
    __tablename__ = 'Topic'
    id = sqlalchemy.Column(sqlalchemy.String(200), primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(100))

    @validates('name')
    def validate_trunc(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value

    def __init__(self, id, name):
        self.name = name


class Place(Base):
    __tablename__ = 'Place'
    id = sqlalchemy.Column(sqlalchemy.String(200), primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(100))
    ptype = sqlalchemy.Column(sqlalchemy.String(10))
    city = sqlalchemy.Column(sqlalchemy.String(25))
    country = sqlalchemy.Column(sqlalchemy.String(25))
    lat = sqlalchemy.Column(sqlalchemy.Float())
    lon = sqlalchemy.Column(sqlalchemy.Float())
    street = sqlalchemy.Column(sqlalchemy.String(100))
    children = relationship('Place',
                            secondary=place_topic,
                            backref='places')
    zip = sqlalchemy.Column(sqlalchemy.String(6))

    @validates('name', 'ptype', 'street', 'country', 'zip')
    def validate_trunc(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value

    def __init__(self, id, name, ptype, city, country, lat, lon, street, zip):
        self.id = id
        self.name = name
        self.ptype = ptype
        self.city = city
        self.country = country
        self.lat = lat
        self.lon = lon
        self.street = street
        self.zip = zip

    def __repr__(self):
        return '<Place {} - {}>'.format(self.id, self.name)

    def __str__(self):
        return '<Place {} - {}>'.format(self.id, self.name)


class Event(Base):
    __tablename__ = 'Event'
    id = sqlalchemy.Column(sqlalchemy.String(200), primary_key=True)
    description = sqlalchemy.Column(sqlalchemy.String(10000))
    name = sqlalchemy.Column(sqlalchemy.String(100))
    picture_url = sqlalchemy.Column(sqlalchemy.String(150))
    ticket_url = sqlalchemy.Column(sqlalchemy.String(150))
    start_time = sqlalchemy.Column(sqlalchemy.DateTime)

    place_id = sqlalchemy.Column(sqlalchemy.String(
        50), sqlalchemy.ForeignKey('Place.id'))
    place = relationship('Place', backref='events', foreign_keys=[place_id])

    @validates('description', 'name')
    def validate_trunc(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value

    @validates('picture_url', 'ticket_url')
    def validate_strict(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return 'None'
        return value

    def __init__(self, id, desc, name, pic_url, tick_url, start_time, place_id):
        self.id = id
        self.description = desc
        self.name = name
        self.picture_url = pic_url
        self.ticket_url = tick_url
        self.start_time = start_time
        self.place_id = place_id

    def __repr__(self):
        return '<Event {} - {}>'.format(self.id, self.name)

    def __str__(self):
        return '<Event {} - {}>'.format(self.id, self.name)

#
# class Page(Base):
#     __tablename__ = 'Page'
#     id = sqlalchemy.Column(sqlalchemy.String(50), primary_key=True)
#     message = sqlalchemy.Column(sqlalchemy.String(10000))
#     link = sqlalchemy.Column(sqlalchemy.String(150))
#     created_time = sqlalchemy.Column(sqlalchemy.DateTime)
#
#     like = sqlalchemy.Column(sqlalchemy.Integer())
#     love = sqlalchemy.Column(sqlalchemy.Integer())
#     haha = sqlalchemy.Column(sqlalchemy.Integer())
#     wow = sqlalchemy.Column(sqlalchemy.Integer())
#     sad = sqlalchemy.Column(sqlalchemy.Integer())
#     angry = sqlalchemy.Column(sqlalchemy.Integer())
#     thankful = sqlalchemy.Column(sqlalchemy.Integer())
#
#     page_id = sqlalchemy.Column(sqlalchemy.String(50), sqlalchemy.ForeignKey('Page.id'))
#     page = relationship('Page', backref='posts', foreign_keys=[page_id])
#
#     @validates('message')
#     def validate_trunc(self, key, value):
#         max_len = getattr(self.__class__, key).prop.columns[0].type.length
#         if value and len(value) > max_len:
#             return value[:max_len]
#         return value
#
#     @validates('link')
#     def validate_strict(self, key, value):
#         max_len = getattr(self.__class__, key).prop.columns[0].type.length
#         if value and len(value) > max_len:
#             return 'None'
#         return value
#
#     def __init__(self, id, page_id, message, link, created_time, like, love, haha, wow, sad, angry, thankful):
#         self.id = id
#         self.message = message
#         self.page_id = page_id
#         self.message = message
#         self.link = link
#         self.created_time = created_time
#         self.like = like
#         self.love = love
#         self.haha = haha
#         self.wow = wow
#         self.sad = sad
#         self.angry = angry
#         self.thankful = thankful
#
#     def __repr__(self):
#         return '<Post {} - {}>'.format(self.id, self.message[:25])
#
#     def __str__(self):
#         return '<Post {} - {}>'.format(self.id, self.message[:25])


#
# class Post(Base):
#     __tablename__ = 'Post'
#     id = sqlalchemy.Column(sqlalchemy.String(50), primary_key=True)
#     message = sqlalchemy.Column(sqlalchemy.String(10000))
#     link = sqlalchemy.Column(sqlalchemy.String(150))
#     created_time = sqlalchemy.Column(sqlalchemy.DateTime)
#
#     like = sqlalchemy.Column(sqlalchemy.Integer())
#     love = sqlalchemy.Column(sqlalchemy.Integer())
#     haha = sqlalchemy.Column(sqlalchemy.Integer())
#     wow = sqlalchemy.Column(sqlalchemy.Integer())
#     sad = sqlalchemy.Column(sqlalchemy.Integer())
#     angry = sqlalchemy.Column(sqlalchemy.Integer())
#     thankful = sqlalchemy.Column(sqlalchemy.Integer())
#
#     page_id = sqlalchemy.Column(sqlalchemy.String(
#         50), sqlalchemy.ForeignKey('Page.id'))
#     page = relationship('Page', backref='posts', foreign_keys=[page_id])
#
#     @validates('message')
#     def validate_trunc(self, key, value):
#         max_len = getattr(self.__class__, key).prop.columns[0].type.length
#         if value and len(value) > max_len:
#             return value[:max_len]
#         return value
#
#     @validates('link')
#     def validate_strict(self, key, value):
#         max_len = getattr(self.__class__, key).prop.columns[0].type.length
#         if value and len(value) > max_len:
#             return 'None'
#         return value
#
#     def __init__(self, id, page_id, message, link, created_time, like, love, haha, wow, sad, angry, thankful):
#         self.id = id
#         self.message = message
#         self.page_id = page_id
#         self.link = link
#         self.created_time = created_time
#         self.like = like
#         self.love = love
#         self.haha = haha
#         self.wow = wow
#         self.sad = sad
#         self.angry = angry
#         self.thankful = thankful
#
#     def __repr__(self):
#         return '<Post {} - {}>'.format(self.id, self.message[:25])
#
#     def __str__(self):
#         return '<Post {} - {}>'.format(self.id, self.message[:25])
#
#
try:
    Base.metadata.create_all(db)
except Exception as e:
    print(e)
    pass


class Storage:
    def __init__(self):
        Session = sessionmaker()
        Session.configure(bind=db)
        self.session = Session()
        self.db = db

    def save_event(self, event, commit=True):
        try:
            event = Event(id=event.get('id', '0'), desc=event.get('description', 'None'),
                          name=event.get('name', 'Unnamed'),
                          pic_url=event.get('picture', {}).get(
                              'data', {}).get('url', 'None'),
                          tick_url=event.get('ticket_uri', 'None'), place_id=event.get('place_id', '0'),
                          start_time=dateutil.parser.parse(event.get('start_time', '2017-04-07T16:00:00+0200')))
            self.session.add(event)
            if commit:
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(e)

    def save_place(self, place, commit=True):
        try:
            place_loc = place.get('location', {})
            place = Place(id=place.get('id', '0'), name=place.get('name', 'Unnamed'),
                          city=place_loc.get('city', 'Wroclaw'), country=place_loc.get('country', 'Poland'),
                          lat=place_loc.get('latitude', 0.0), lon=place_loc.get('longitude', 0.0),
                          street=place_loc.get('street', 'Unknown'), zip=place_loc.get('zip', '00-000'))
            self.session.add(place)
            if commit:
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(e)

    def save_post(self):
        pass

    def save_page(self):
        pass

    def event_exists(self, event_id):
        return True if self.session.query(Event.id).filter_by(id=event_id).scalar() is not None else False

    def place_exists(self, place_id):
        return True if self.session.query(Place.id).filter_by(id=place_id).scalar() is not None else False


if __name__ == '__main__':
    s = Storage()
