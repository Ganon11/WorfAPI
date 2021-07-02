import hashlib
import json
from flask import Flask
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

def fetch_memory():
  '''Reads a json file and returns the equivalent object.'''
  with open('data/memory.json', 'r') as fh:
    return json.load(fh)

def save_memory(obj):
  '''Dumps an object as a json string into a file.'''
  with open('data/memory.json', 'w') as fh:
    fh.write(json.dumps(obj))

def create_response(response_type, text):
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

  def _format_response(self, text, honorable):
    if honorable:
      return create_response('in_channel', f'{text} has honor.')

    return create_response('in_channel', f'{text} is without honor.')

  def post(self):
    '''Returns a phrase describing the honor of the input.'''
    parser = reqparse.RequestParser()
    parser.add_argument('text', required=True)
    args = parser.parse_args()

    is_honorable = self._get_honor(args.text.lower())
    return self._format_response(args.text, is_honorable), 200

class SetHonor(Resource): # pylint: disable=too-few-public-methods
  '''Overrides the honor value for a given input phrase.'''

  def __init__(self):
    self.memory = fetch_memory()

  def _format_response(self, text, honorable):
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
      return 'Invalid request format: should be "phrase:true" or "phrase:false"', 400

    topic = values[0].lower()
    is_honorable = values[1].lower()

    if is_honorable == 'true':
      if topic not in self.memory['honor']:
        self.memory['honor'].append(topic)

      if topic in self.memory['dishonor']:
        self.memory['dishonor'].remove(topic)
    elif is_honorable == 'false':
      if topic not in self.memory['dishonor']:
        self.memory['dishonor'].append(topic)

      if topic in self.memory['honor']:
        self.memory['honor'].remove(topic)
    else:
      return 'Invalid request format: should be "phrase:true" or "phrase:false"', 400

    save_memory(self.memory)
    return self._format_response(values[0], is_honorable == 'true'), 200

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
    if topic in self.memory['honor']:
      self.memory['honor'].remove(topic)
    elif topic in self.memory['dishonor']:
      self.memory['dishonor'].remove(topic)
    else:
      return f'{args.text} was not found', 404

    save_memory(self.memory)
    return create_response('ephemeral', f'{args.text} has been forgotten.'), 200

api.add_resource(Honor, '/honor')
api.add_resource(SetHonor, '/sethonor')
api.add_resource(RemoveHonor, '/removehonor')

if __name__ == '__main__':
  app.run()
