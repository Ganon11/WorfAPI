'''A simple Flask API to help determine whether someone or something is honorable.'''

import hashlib
import os
from flask import Flask
from flask_restful import Resource, Api, reqparse
import inflect
import psycopg2

app = Flask(__name__)
api = Api(app)

DATABASE_URL = os.environ['DATABASE_URL']

def fetch_memory():
  '''
  Reads the list of honorable and dishonorable topics from the database, and returns an object
  containing both lists.
  '''
  honorable = set()
  dishonorable = set()
  with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
    honor_cursor = conn.cursor()
    honor_cursor.execute('SELECT "Topic" FROM "Honorable"')
    rows = honor_cursor.fetchall()
    for row in rows:
      honorable.add(row[0][0])

    dishonor_cursor = conn.cursor()
    dishonor_cursor.execute('SELECT "Topic" FROM "Dishonorable"')
    rows = dishonor_cursor.fetchall()
    for row in rows:
      dishonorable.add(row[0][0])

  memory = dict()
  memory['honor'] = honorable
  memory['dishonor'] = dishonorable
  return memory

def save_memory(obj):
  '''Dumps an object describing honorable and dishonorable topics to the database.'''
  with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
    honor_cursor = conn.cursor()
    honor_cursor.execute('SELECT "Topic" FROM "Honorable"')
    rows = honor_cursor.fetchall()
    honorable = set()
    for row in rows:
      honorable.add(row[0][0])

    topics_to_add = (obj['honor'] - honorable)
    topics_to_remove = (honorable - obj['honor'])
    for topic in topics_to_remove:
      honor_cursor.execute('DELETE FROM "Honorable" WHERE "Topic" = %s', ("{{{}}}".format(topic),))
    for topic in topics_to_add:
      honor_cursor.execute('INSERT INTO "Honorable" ("Topic") VALUES (%s)', ("{{{}}}".format(topic),))

    dishonor_cursor = conn.cursor()
    dishonor_cursor.execute('SELECT "Topic" FROM "Dishonorable"')
    rows = dishonor_cursor.fetchall()
    dishonorable = set()
    for row in rows:
      dishonorable.add(row[0][0])

    topics_to_add = (obj['dishonor'] - dishonorable)
    topics_to_remove = (dishonorable - obj['dishonor'])
    for topic in topics_to_remove:
      dishonor_cursor.execute('DELETE FROM "Dishonorable" WHERE "Topic" = %s', ("{{{}}}".format(topic),))
    for topic in topics_to_add:
      honor_cursor.execute('INSERT INTO "Dishonorable" ("Topic") VALUES (%s)', ("{{{}}}".format(topic),))

def create_response(response_type, text):
  '''Creates a response object that Slack will understand.'''
  response = dict()
  response['response_type'] = response_type
  response['text'] = text
  return response

class Honor(Resource): # pylint: disable=too-few-public-methods
  '''Determines whether the given input has honor or not.'''

  def __init__(self):
    self.memory = fetch_memory()

  def _get_honor(self, topic):
    '''Returns True if the phrase is honorable, False otherwise.'''
    if topic in self.memory['honor']:
      return True
    if topic in self.memory['dishonor']:
      return False

    hasher = hashlib.md5()
    hasher.update(topic.encode('utf-8'))
    if hasher.hexdigest()[-1] in ['0', '1', '2', '3', '4', '5', '6', '7']:
      return True

    return False

  @staticmethod
  def _format_response(text, honorable):
    engine = inflect.engine()
    if honorable:
      verb = 'has'
      if engine.singular_noun(text):
        verb = 'have'
      return create_response('in_channel', f'{text} {verb} honor.')

    verb = 'is'
    if engine.singular_noun(text):
      verb = 'are'
    return create_response('in_channel', f'{text} {verb} without honor.')

  def post(self):
    '''Returns a phrase describing the honor of the input.'''
    parser = reqparse.RequestParser()
    parser.add_argument('text', required=True)
    args = parser.parse_args()

    is_honorable = self._get_honor(args.text.lower())
    return Honor._format_response(args.text, is_honorable), 200

class SetHonor(Resource): # pylint: disable=too-few-public-methods
  '''Overrides the honor value for a given input phrase.'''

  def __init__(self):
    self.memory = fetch_memory()

  @staticmethod
  def _format_response(text, honorable):
    if honorable:
      return create_response('ephemeral', f'{text} will be remembered as honorable.')

    return create_response('ephemeral', f'{text} will be remembered as dishonorable.')

  def post(self):
    '''Adds a phrase to the known list of honorable/dishonorable phrases.'''
    parser = reqparse.RequestParser()
    parser.add_argument('text', required=True)
    args = parser.parse_args()

    values = args.text.split(':')
    if len(values) != 2:
      return create_response('ephemeral', 'Invalid request format: should be "phrase:true" or "phrase:false"'), 200

    topic = values[0].lower()
    is_honorable = values[1].lower()

    if is_honorable == 'true':
      if topic not in self.memory['honor']:
        self.memory['honor'].add(topic)

      if topic in self.memory['dishonor']:
        self.memory['dishonor'].remove(topic)
    elif is_honorable == 'false':
      if topic not in self.memory['dishonor']:
        self.memory['dishonor'].add(topic)

      if topic in self.memory['honor']:
        self.memory['honor'].remove(topic)
    else:
      return create_response('ephemeral', 'Invalid request format: should be "phrase:true" or "phrase:false"'), 200

    save_memory(self.memory)
    return SetHonor._format_response(values[0], is_honorable == 'true'), 200

class RemoveHonor(Resource): # pylint: disable=too-few-public-methods
  '''Removes an overriden value for a given input phrase.'''

  def __init__(self):
    self.memory = fetch_memory()

  def post(self):
    '''Deletes a phrase from the known list of honorable/dishonorable phrases.'''
    parser = reqparse.RequestParser()
    parser.add_argument('text', required=True)
    args = parser.parse_args()

    topic = args.text.lower()
    engine = inflect.engine()
    if topic in self.memory['honor']:
      self.memory['honor'].remove(topic)
    elif topic in self.memory['dishonor']:
      self.memory['dishonor'].remove(topic)
    else:
      verb = 'was'
      if engine.singular_noun(args.text):
        verb = 'were'
      return create_response('ephemeral', f'{args.text} {verb} not found'), 200

    save_memory(self.memory)
    verb = 'has'
    if engine.singular_noun(args.text):
      verb = 'have'
    return create_response('ephemeral', f'{args.text} {verb} been forgotten.'), 200

api.add_resource(Honor, '/honor')
api.add_resource(SetHonor, '/sethonor')
api.add_resource(RemoveHonor, '/removehonor')

if __name__ == '__main__':
  app.run()
