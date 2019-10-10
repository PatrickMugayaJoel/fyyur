#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import sys
import datetime
import logging
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    start_time = db.Column(db.String, nullable=False)

    venue = db.relationship("Venue", backref=db.backref("shows", lazy=True))
    artist = db.relationship("Artist", backref=db.backref("shows", lazy=True))

    def __init__(self, artist=None, venue=None, start_time=None):
      self.artist = artist
      self.venue =  venue
      self.start_time = start_time

    def __repr__(self):
      return f'<Show: { self.artist.name } at { self.venue.name }>'

    # db.Column('start_time', db.String, default=datetime.utcnow().isoformat())
    # timestamp = moment.create(datetime.utcnow()).calendar()
    # moment(that time).unix().format(format_string=None)
    # from app import db Venue Artist

venue_genres = db.Table('venue_genres',
    db.Column('venue_id', db.Integer, db.ForeignKey('venue.id')),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'))
)

artist_genres = db.Table('artist_genres',
    db.Column('artist_id', db.Integer, db.ForeignKey('artist.id')),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'))
)

class Genre(db.Model):
    __tablename__ = 'genre'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    def __repr__(self):
      return f'<Genre: { self.name }>'

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean())
    seeking_description = db.Column(db.Text())
    genres = db.relationship("Genre", secondary=venue_genres,
      backref=db.backref('venues', lazy=True))
    artists = db.relationship("Artist", secondary='show', viewonly=True)

    def add_shows(self, items):
      for artist, start_time in items:
        self.shows.append(Show(venue=self, artist=artist, start_time=start_time))

    def __repr__(self):
      return f'<Venue { self.name }>'

class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean())
    seeking_description = db.Column(db.Text())
    genres = db.relationship("Genre", secondary=artist_genres,
      backref=db.backref('artists', lazy=True))
    venues = db.relationship("Venue", secondary='show', viewonly=True)

    def add_shows(self, items):
      for venue, start_time in items:
        self.shows.append(Show(venue=venue, artist=self, start_time=start_time))

    def __repr__(self):
      return f'<Artist { self.name }>'

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  data = []
  allVenues = db.session.query(Venue)
  cities = allVenues.with_entities(Venue.city, Venue.state).distinct().all()
  for city, state in cities:
    theVenues = db.session.query(Venue).filter_by(city=city).all()
    result = {"city": city, "state": state, "venues": []}
    for venue in theVenues:
      upcoming = db.session.query(Show).filter_by(venue_id = venue.id).filter(
        Show.start_time > datetime.utcnow().isoformat()).all()
      result["venues"].append({
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": len(upcoming)
      })
    data.append(result)
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  searchTerm = request.form.get("search_term")
  venues = db.session.query(Venue).with_entities(Venue.id, Venue.name).filter(Venue.name.contains(searchTerm)).all()
  data = []
  for venue in venues:
    upcoming = db.session.query(Show).filter_by(venue_id = venue.id).filter(
      Show.start_time > datetime.utcnow().isoformat()).all()
    data.append({
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": len(upcoming)
    })
  response={
    "count": len(venues),
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

# def SerializeList(items):
#   result = []
#   for item in items:
#     obj = item.__dict__
#     del obj['_sa_instance_state']
#     result.append(obj)
#   return result

def formartShows(shows_list):
  new_list = []
  for show in shows_list:
    artist = show.artist
    new_list.append({
      "artist_id": artist.id,
      "artist_name": artist.name,
      "artist_image_link": artist.image_link,
      "start_time": show.start_time
    })
  return new_list

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = db.session.query(Venue).filter_by(id = venue_id).first()
  
  data = {}
  if venue:
    data = venue.__dict__
    del data['_sa_instance_state']
    
    pastshows = db.session.query(Show).filter_by(venue_id = venue.id).filter(
      Show.start_time < datetime.utcnow().isoformat()).all()
    upcomingshows = db.session.query(Show).filter_by(venue_id = venue.id).filter(
      Show.start_time > datetime.utcnow().isoformat()).all()

    past_shows = formartShows(pastshows)
    upcoming_shows = formartShows(upcomingshows)

    data["past_shows"] = past_shows
    data["upcoming_shows"] = upcoming_shows
    data["past_shows_count"] = len(past_shows)
    data["upcoming_shows_count"] = len(upcoming_shows)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  new_venue = Venue()

  form = VenueForm()
  if not form.validate_on_submit():
    return render_template('forms/new_venue.html', form=form)

  try:
    genres = []
    for genre in request.form.getlist("genres"):
      genres.append(Genre(name=genre))

    new_venue.name = request.form.get("name")
    new_venue.city = request.form.get("city")
    new_venue.state = request.form.get("state")
    new_venue.address = request.form.get("address")
    new_venue.phone = request.form.get("phone")
    new_venue.facebook_link = request.form.get("facebook_link")
    new_venue.genres = genres

    db.session.add(new_venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except Exception as err:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = db.session.query(Venue).filter_by(id = venue_id).first()
    venue_name = venue.name
    db.session.delete(venue)
    db.session.commit()
    flash('Venue ' + venue_name + ' successfully deleted.')
  except Exception as err:
    flash('An error occurred. Venue with id ' + venue_id + ' could not be deleted.')

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = db.session.query(Artist).with_entities(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  data = []
  artists = []

  searchTerm = request.form.get("search_term").lower()
  for artist in db.session.query(Artist).with_entities(Artist.id, Artist.name).all():
    if searchTerm in artist.name.lower():
      artists.append(artist)

  for artist in artists:
    upcoming = db.session.query(Show).filter_by(artist_id = artist.id).filter(
      Show.start_time > datetime.utcnow().isoformat()).all()
    data.append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": len(upcoming)
    })
  response={
    "count": len(artists),
    "data": data
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

def formartArtistShows(shows_list):
  new_list = []
  for show in shows_list:
    venue = show.venue
    new_list.append({
      "venue_id": venue.id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.start_time
    })
  return new_list

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = db.session.query(Artist).filter_by(id = artist_id).first()
  
  data = {}
  if artist:
    data = artist.__dict__
    del data['_sa_instance_state']
    
    pastshows = db.session.query(Show).filter_by(artist_id = artist.id).filter(
      Show.start_time < datetime.utcnow().isoformat()).all()
    upcomingshows = db.session.query(Show).filter_by(artist_id = artist.id).filter(
      Show.start_time > datetime.utcnow().isoformat()).all()

    past_shows = formartArtistShows(pastshows)
    upcoming_shows = formartArtistShows(upcomingshows)

    data["past_shows"] = past_shows
    data["upcoming_shows"] = upcoming_shows
    data["past_shows_count"] = len(past_shows)
    data["upcoming_shows_count"] = len(upcoming_shows)

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistEditForm()
  artist = db.session.query(Artist).filter_by(id = artist_id).first()

  if artist:
    form.name.data = artist.name
    form.city.data = artist.city
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.image_link.data = artist.image_link
    form.genres.data = artist.genres
    form.facebook_link.data = artist.facebook_link
    form.image_link.data = artist.image_link
    form.website.data = artist.website
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description
  
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  artist = db.session.query(Artist).filter_by(id = artist_id).first()

  form = ArtistEditForm()
  if not form.validate_on_submit():
    return render_template('forms/edit_artist.html', form=form, artist=artist)

  try:
    genres = []
    for genre in request.form.getlist("genres"):
      genres.append(Genre(name=genre))

    artist.name = request.form.get("name")
    artist.city = request.form.get("city")
    artist.phone = request.form.get("phone")
    artist.state = request.form.get("state")
    artist.facebook_link = request.form.get("facebook_link")
    artist.genres = genres
    artist.image_link = request.form.get("image_link")
    artist.website = request.form.get("website")
    artist.seeking_venue = int(request.form.get("seeking_venue"))
    artist.seeking_description = request.form.get("seeking_description")

    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  except Exception as err:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueEditForm()
  
  venue = db.session.query(Venue).filter_by(id = venue_id).first()

  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.image_link.data = venue.image_link
  form.genres.data = venue.genres
  form.facebook_link.data = venue.facebook_link
  form.image_link.data = venue.image_link
  form.website.data = venue.website
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description
  
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  venue = db.session.query(Venue).filter_by(id = venue_id).first()

  form = VenueEditForm()
  if not form.validate_on_submit():
    return render_template('forms/edit_venue.html', form=form, venue=venue)

  try:
    genres = []
    for genre in request.form.getlist("genres"):
      genres.append(Genre(name=genre))

    venue.name = request.form.get("name")
    venue.city = request.form.get("city")
    venue.state = request.form.get("state")
    venue.address = request.form.get("address")
    venue.phone = request.form.get("phone")
    venue.facebook_link = request.form.get("facebook_link")
    venue.genres = genres
    venue.image_link = request.form.get("image_link")
    venue.website = request.form.get("website")
    venue.seeking_talent = int(request.form.get("seeking_talent"))
    venue.seeking_description = request.form.get("seeking_description")

    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully updated!')
  except Exception as err:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  artist = Artist()

  form = ArtistForm()
  if not form.validate_on_submit():
    return render_template('forms/new_artist.html', form=form)

  try:
    genres = []
    for genre in request.form.getlist("genres"):
      genres.append(Genre(name=genre))

    artist.name = request.form.get("name")
    artist.city = request.form.get("city")
    artist.phone = request.form.get("phone")
    artist.state = request.form.get("state")
    artist.facebook_link = request.form.get("facebook_link")
    artist.genres = genres

    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except Exception as err:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  show_objs = db.session.query(Show).all()
  
  for obj in show_objs:
    show = {}
    show["venue_id"] = obj.venue_id
    show["venue_name"] = obj.venue.name
    show["artist_id"] = obj.artist_id
    show["artist_name"] = obj.artist.name
    show["artist_image_link"] = obj.artist.image_link
    show["start_time"] = obj.start_time
    data.append(show)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():

  form = ShowForm()
  if not form.validate_on_submit():
    return render_template('forms/new_show.html', form=form)

  try:
    venue = db.session.query(Venue).filter_by(id = request.form.get("venue_id")).first()
    show = Show(start_time=request.form.get("start_time"))
    show.artist = db.session.query(Artist).filter_by(id = request.form.get("artist_id")).first()
    show.venue = venue

    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except Exception as err:
    flash('An error occurred. Show could not be listed.')
    print(err)

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
